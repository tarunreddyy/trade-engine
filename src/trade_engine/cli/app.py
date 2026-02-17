import json
import sys
from datetime import datetime
from pathlib import Path

from rich.panel import Panel
from rich.table import Table

from trade_engine.brokers.broker_factory import BrokerFactory
from trade_engine.brokers.sdk_manager import get_broker_sdk_status
from trade_engine.cli.ai_advisor_menu import AIAdvisorMenu
from trade_engine.cli.interface import CLInterface
from trade_engine.cli.settings_menu import SettingsMenu
from trade_engine.cli.strategy_menu import StrategyMenu
from trade_engine.cli.visualization_menu import VisualizationMenu
from trade_engine.config.broker_config import get_active_broker
from trade_engine.config.trading_config import (
    get_live_dashboard_control_file,
    get_live_dashboard_port,
    get_live_dashboard_state_file,
    get_live_session_state_file,
    get_order_journal_file,
)
from trade_engine.core.market_data_service import MarketDataService
from trade_engine.core.portfolio_chatbot import PortfolioChatbot
from trade_engine.core.vector_db_search import VectorDBSearch
from trade_engine.engine.order_journal import OrderJournal
from trade_engine.web.live_dashboard import LiveDashboardServer, write_dashboard_state


class TraderCLI:
    def __init__(self):
        self.interface = CLInterface()
        self.session_started_at = datetime.utcnow().isoformat()
        self.market_data = MarketDataService()
        self.dashboard_server: LiveDashboardServer | None = None
        self.order_journal = OrderJournal(get_order_journal_file())
        self.settings_menu = SettingsMenu(self.interface)
        self._refresh_runtime_components(initial_boot=True)

    def _refresh_runtime_components(self, initial_boot: bool = False):
        if self.dashboard_server:
            self.dashboard_server.stop()
            self.dashboard_server = None
        self.broker = BrokerFactory.create_broker()
        self.order_journal = OrderJournal(get_order_journal_file())
        status = get_broker_sdk_status(get_active_broker())
        if not status["installed"]:
            missing = ", ".join(status["missing_imports"])
            self.interface.print_info(
                f"Active broker SDK is not fully installed (missing: {missing}). "
                "Open Settings -> Broker SDKs to install from CLI."
            )
        self.vector_search = None
        self.chatbot = None
        self.viz_menu = VisualizationMenu(self.interface)
        self.strategy_menu = StrategyMenu(self.interface, broker=self.broker)
        self.ai_advisor_menu = AIAdvisorMenu(self.interface)
        if not initial_boot:
            self.interface.print_success("Runtime services refreshed with latest CLI settings.")

    @staticmethod
    def _read_json(path: str) -> dict:
        target = Path(path)
        if not target.exists():
            return {}
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _ensure_dashboard_server(self, open_browser: bool = False) -> str:
        if self.dashboard_server:
            return self.dashboard_server.url
        self.dashboard_server = LiveDashboardServer(
            host="127.0.0.1",
            port=get_live_dashboard_port(),
            state_file=get_live_dashboard_state_file(),
            control_file=get_live_dashboard_control_file(),
        )
        return self.dashboard_server.start(open_browser=open_browser)

    def _write_dashboard_fallback_state(self):
        state_file = get_live_dashboard_state_file()
        watchlist_symbols = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS"]
        watchlist_rows = self.market_data.get_batch_snapshot(watchlist_symbols, exchange="NSE", segment="CASH")
        payload = {
            "strategy_name": "No live strategy running",
            "mode": "paper",
            "watchlist": [
                {
                    "symbol": row.get("symbol"),
                    "price": row.get("ltp"),
                    "change_pct": row.get("change_pct"),
                    "signal": 0,
                    "signal_text": "HOLD",
                    "buy_enabled": True,
                    "sell_enabled": True,
                }
                for row in watchlist_rows
            ],
            "indices": self.market_data.get_indices_snapshot(),
            "fno": self.market_data.get_fno_snapshot(),
            "positions": [],
            "open_orders": [],
            "closed_orders": [],
            "signal_triggers": [],
            "session": {
                "started_at": self.session_started_at,
                "total_orders": 0,
                "open_orders": 0,
                "closed_orders": 0,
            },
            "message": "Market data fallback mode (no active live strategy session).",
        }
        write_dashboard_state(state_file, payload)

    def _render_main_session_header(self):
        state = self._read_json(get_live_session_state_file())
        positions = state.get("positions", []) if isinstance(state.get("positions"), list) else []
        symbols = sorted({str(row.get("symbol", "")).upper() for row in positions if row.get("symbol")})
        summary = self.order_journal.get_session_summary(since_iso=self.session_started_at, limit=5)

        grid = Table.grid(expand=True)
        grid.add_column(justify="left")
        grid.add_column(justify="left")
        grid.add_column(justify="left")
        grid.add_column(justify="left")
        grid.add_row(
            f"[cyan]Broker:[/cyan] {get_active_broker()}",
            f"[green]Holdings:[/green] {len(symbols)}",
            f"[yellow]Open Trades:[/yellow] {summary.get('open_orders', 0)}",
            f"[magenta]Closed Trades:[/magenta] {summary.get('closed_orders', 0)}",
        )
        holdings_text = ", ".join(symbols[:8]) if symbols else "-"
        if len(symbols) > 8:
            holdings_text += f", +{len(symbols) - 8} more"
        grid.add_row(
            f"[dim]Session started:[/dim] {self.session_started_at}",
            f"[dim]Holdings symbols:[/dim] {holdings_text}",
            f"[dim]Orders total:[/dim] {summary.get('total_orders', 0)}",
            "",
        )
        self.interface.console.print(Panel(grid, title="Current Session", border_style="cyan"))

    def run(self):
        while True:
            try:
                self.interface.clear_screen()
                self.interface.print_banner()
                self._render_main_session_header()
                main_menu = [
                    "Quick Setup",
                    "Orders",
                    "Portfolio",
                    "Market Data",
                    "Search",
                    "AI Search",
                    "Chatbot",
                    "Charts",
                    "Strategies",
                    "AI Advisor",
                    "Settings",
                    "Exit",
                ]
                choice = self.interface.show_menu(main_menu, "Main Menu", clear_screen=False)

                if choice == "Quick Setup":
                    changed = self.settings_menu.quick_setup()
                    if changed:
                        self._refresh_runtime_components()
                elif choice == "Orders":
                    self.handle_orders_menu()
                elif choice == "Portfolio":
                    self.handle_portfolio_menu()
                elif choice == "Market Data":
                    self.handle_live_data_menu()
                elif choice == "Search":
                    self.handle_search_menu()
                elif choice == "AI Search":
                    self.handle_vector_search_menu()
                elif choice == "Chatbot":
                    self.handle_chatbot_menu()
                elif choice == "Charts":
                    self.viz_menu.show()
                elif choice == "Strategies":
                    if self.dashboard_server:
                        self.dashboard_server.stop()
                        self.dashboard_server = None
                    self.strategy_menu.show()
                elif choice == "AI Advisor":
                    self.ai_advisor_menu.show()
                elif choice == "Settings":
                    changed = self.settings_menu.show()
                    if changed:
                        self._refresh_runtime_components()
                elif choice == "Exit":
                    if self.dashboard_server:
                        self.dashboard_server.stop()
                        self.dashboard_server = None
                    self.interface.typing_effect("Thank you for using TradeEngine CLI!", delay=0.02, style="bold cyan")
                    sys.exit(0)
            except KeyboardInterrupt:
                if self.dashboard_server:
                    self.dashboard_server.stop()
                    self.dashboard_server = None
                self.interface.print_info("\nExiting...")
                sys.exit(0)
            except Exception as error:
                self.interface.print_error(f"An error occurred: {str(error)}")

    def handle_orders_menu(self):
        menu_options = [
            "Place Order",
            "Modify Order",
            "Cancel Order",
            "Get Order Status",
            "Get Order List",
            "Get Order Details",
            "Get Trades Details",
            "Back to Main Menu",
        ]
        choice = self.interface.show_menu(menu_options, "Orders Management")
        if choice == "Place Order":
            self.place_order()
        elif choice == "Modify Order":
            self.modify_order()
        elif choice == "Cancel Order":
            self.cancel_order()
        elif choice == "Get Order Status":
            self.get_order_status()
        elif choice == "Get Order List":
            self.get_order_list()
        elif choice == "Get Order Details":
            self.get_order_details()
        elif choice == "Get Trades Details":
            self.get_trades_details()

    def place_order(self):
        symbol = self.interface.input_prompt("Enter trading symbol: ")
        quantity = int(self.interface.input_prompt("Enter quantity: "))
        price = float(self.interface.input_prompt("Enter price: "))
        result = self.interface.show_loading(
            "[bold cyan]Placing order...[/bold cyan]",
            self.broker.place_order,
            trading_symbol=symbol,
            quantity=quantity,
            price=price,
        )
        if result:
            self.interface.display_response(result, "Order Placed")
            self.interface.print_success("Order placed successfully!")

    def modify_order(self):
        order_id = self.interface.input_prompt("Enter order ID: ")
        quantity = int(self.interface.input_prompt("Enter new quantity: "))
        price = float(self.interface.input_prompt("Enter new price: "))
        result = self.interface.show_loading(
            "[bold cyan]Modifying order...[/bold cyan]",
            self.broker.modify_order,
            order_id=order_id,
            quantity=quantity,
            price=price,
        )
        if result:
            self.interface.display_response(result, "Order Modified")
            self.interface.print_success("Order modified successfully!")

    def cancel_order(self):
        order_id = self.interface.input_prompt("Enter order ID: ")
        result = self.interface.show_loading(
            "[bold cyan]Cancelling order...[/bold cyan]",
            self.broker.cancel_order,
            order_id=order_id,
        )
        if result:
            self.interface.display_response(result, "Order Cancelled")
            self.interface.print_success("Order cancelled successfully!")

    def get_order_status(self):
        order_id = self.interface.input_prompt("Enter order ID: ")
        result = self.interface.show_loading(
            "[bold cyan]Fetching order status...[/bold cyan]",
            self.broker.get_order_status,
            order_id=order_id,
        )
        if result:
            self.interface.display_response(result, "Order Status")

    def get_order_list(self):
        result = self.interface.show_loading(
            "[bold cyan]Fetching order list...[/bold cyan]",
            self.broker.get_order_list,
        )
        if result:
            self.interface.display_response(result, "Order List")

    def get_order_details(self):
        order_id = self.interface.input_prompt("Enter order ID: ")
        result = self.interface.show_loading(
            "[bold cyan]Fetching order details...[/bold cyan]",
            self.broker.get_order_details,
            order_id=order_id,
        )
        if result:
            self.interface.display_response(result, "Order Details")

    def get_trades_details(self):
        order_id = self.interface.input_prompt("Enter order ID: ")
        result = self.interface.show_loading(
            "[bold cyan]Fetching trades details...[/bold cyan]",
            self.broker.get_trades_details,
            order_id=order_id,
        )
        if result:
            self.interface.display_response(result, "Trade Details")

    def handle_portfolio_menu(self):
        menu_options = [
            "Get Portfolio Holdings",
            "Get Positions (CASH)",
            "Get Positions (FUTURES)",
            "Get All Positions",
            "Back to Main Menu",
        ]
        choice = self.interface.show_menu(menu_options, "Portfolio and Positions")

        if choice == "Get Portfolio Holdings":
            result = self.interface.show_loading("[bold cyan]Fetching portfolio...[/bold cyan]", self.broker.get_portfolio)
            if result:
                self.interface.display_response(result, "Portfolio Holdings")
        elif choice == "Get Positions (CASH)":
            result = self.interface.show_loading(
                "[bold cyan]Fetching CASH positions...[/bold cyan]",
                self.broker.get_positions,
                segment="CASH",
            )
            if result:
                self.interface.display_response(result, "CASH Positions")
        elif choice == "Get Positions (FUTURES)":
            result = self.interface.show_loading(
                "[bold cyan]Fetching FUTURES positions...[/bold cyan]",
                self.broker.get_positions,
                segment="FUTURES",
            )
            if result:
                self.interface.display_response(result, "FUTURES Positions")
        elif choice == "Get All Positions":
            result = self.interface.show_loading(
                "[bold cyan]Fetching all positions...[/bold cyan]",
                self.broker.get_positions,
            )
            if result:
                self.interface.display_response(result, "All Positions")

    def handle_live_data_menu(self):
        menu_options = [
            "Open Web Dashboard (localhost)",
            "Refresh Dashboard Fallback Data",
            "NSE + F&O Snapshot",
            "Get Live Quote",
            "Get LTP (Last Traded Price)",
            "Side-by-Side Comparison",
            "Back to Main Menu",
        ]
        choice = self.interface.show_menu(menu_options, "Live Market Data")

        if choice == "Open Web Dashboard (localhost)":
            try:
                self._write_dashboard_fallback_state()
                url = self._ensure_dashboard_server(open_browser=True)
                self.interface.print_success(f"Dashboard running at {url}")
            except Exception as error:
                self.interface.print_error(f"Unable to start dashboard: {error}")
        elif choice == "Refresh Dashboard Fallback Data":
            try:
                self._write_dashboard_fallback_state()
                self.interface.print_success("Dashboard fallback data refreshed.")
            except Exception as error:
                self.interface.print_error(f"Could not refresh fallback market data: {error}")
        elif choice == "NSE + F&O Snapshot":
            indices = self.interface.show_loading(
                "[bold cyan]Fetching NSE indices...[/bold cyan]",
                self.market_data.get_indices_snapshot,
            )
            fno = self.interface.show_loading(
                "[bold cyan]Fetching F&O watch...[/bold cyan]",
                self.market_data.get_fno_snapshot,
            )
            if indices or fno:
                self.interface.display_side_by_side(
                    indices or [{"status": "No index data"}],
                    fno or [{"status": "No F&O data"}],
                    left_title="NSE Index Snapshot",
                    right_title="F&O Snapshot",
                )
        elif choice == "Get Live Quote":
            symbol = self.interface.input_prompt("Enter trading symbol: ")
            exchange = self.interface.input_prompt("Enter exchange (NSE/BSE): ", style="bold yellow") or "NSE"
            segment = self.interface.input_prompt("Enter segment (CASH/FUTURES): ", style="bold yellow") or "CASH"
            result = self.interface.show_loading(
                "[bold cyan]Fetching live quote...[/bold cyan]",
                self.broker.get_quote,
                trading_symbol=symbol,
                exchange=exchange,
                segment=segment,
            )
            if result:
                self.interface.display_response(result, f"Live Quote - {symbol}")

        elif choice == "Get LTP (Last Traded Price)":
            symbol = self.interface.input_prompt("Enter trading symbol: ")
            exchange = self.interface.input_prompt("Enter exchange (NSE/BSE): ", style="bold yellow") or "NSE"
            segment = self.interface.input_prompt("Enter segment (CASH/FUTURES): ", style="bold yellow") or "CASH"
            result = self.interface.show_loading(
                "[bold cyan]Fetching LTP...[/bold cyan]",
                self.broker.get_ltp,
                trading_symbol=symbol,
                exchange=exchange,
                segment=segment,
            )
            if result:
                self.interface.display_response(result, f"LTP - {symbol}")

        elif choice == "Side-by-Side Comparison":
            symbol1 = self.interface.input_prompt("Enter first symbol: ")
            symbol2 = self.interface.input_prompt("Enter second symbol: ")
            exchange = self.interface.input_prompt("Enter exchange (NSE/BSE): ", style="bold yellow") or "NSE"
            segment = self.interface.input_prompt("Enter segment (CASH/FUTURES): ", style="bold yellow") or "CASH"
            result1 = self.interface.show_loading(
                f"[bold cyan]Fetching {symbol1}...[/bold cyan]",
                self.broker.get_quote,
                trading_symbol=symbol1,
                exchange=exchange,
                segment=segment,
            )
            result2 = self.interface.show_loading(
                f"[bold cyan]Fetching {symbol2}...[/bold cyan]",
                self.broker.get_quote,
                trading_symbol=symbol2,
                exchange=exchange,
                segment=segment,
            )
            if result1 and result2:
                self.interface.display_side_by_side(
                    result1,
                    result2,
                    left_title=f"{symbol1} Quote",
                    right_title=f"{symbol2} Quote",
                )

    def handle_search_menu(self):
        query = self.interface.input_prompt("Enter search query: ")
        exchange = self.interface.input_prompt("Enter exchange (NSE/BSE): ", style="bold yellow") or "NSE"
        result = self.interface.show_loading(
            "[bold cyan]Searching instruments...[/bold cyan]",
            self.broker.search_instrument,
            symbol=query,
            exchange=exchange,
        )
        if result:
            self.interface.display_response(result, "Search Results")

    def handle_vector_search_menu(self):
        if self.vector_search is None:
            try:
                self.vector_search = VectorDBSearch()
            except Exception as error:
                self.interface.print_error(f"Vector search unavailable: {error}")
                return

        query = self.interface.input_prompt("Enter search query: ")
        result = self.interface.show_loading(
            "[bold cyan]AI is searching...[/bold cyan]",
            self.vector_search.search,
            query=query,
        )
        if result:
            self.interface.display_response(result, "AI Vector Search Results")

    def handle_chatbot_menu(self):
        if self.chatbot is None:
            try:
                self.chatbot = PortfolioChatbot(broker=self.broker)
            except Exception as error:
                self.interface.print_error(f"Portfolio chatbot unavailable: {error}")
                return

        self.interface.print_info("Starting Portfolio Chatbot...")
        self.interface.print_info("Type 'exit'/'quit' to return, 'reset' to clear chat, 'refresh' to reload data.")
        self.interface.print_info("=" * 60)

        try:
            greeting = self.interface.show_loading(
                "[bold cyan]Portfolio Bot is thinking...[/bold cyan]",
                self.chatbot.chat,
                "Hello! I'd like to chat about my portfolio.",
            )
            if greeting:
                self.interface.console.print(f"\n[bold cyan]Portfolio Bot:[/bold cyan] {greeting}\n")
        except Exception as error:
            self.interface.print_error(f"Error initializing chatbot: {str(error)}")
            return

        while True:
            try:
                user_input = self.interface.input_prompt(
                    "You: ",
                    style="bold green",
                    slash_commands={
                        "/refresh": "Reload portfolio data",
                        "/reset": "Reset conversation",
                        "/exit": "Exit chatbot",
                    },
                )
                command = user_input.lower().strip()
                if command in {"exit", "quit", "back", "/exit", "/quit", "/back"}:
                    self.interface.print_info("Exiting chatbot...")
                    break
                if command in {"reset", "/reset"}:
                    self.chatbot.reset_conversation()
                    self.interface.print_success("Conversation reset!")
                    continue
                if command in {"refresh", "/refresh"}:
                    response = self.interface.show_loading(
                        "[bold cyan]Portfolio Bot is refreshing and thinking...[/bold cyan]",
                        self.chatbot.chat,
                        "Please refresh the portfolio data.",
                        refresh_data=True,
                    )
                    if response:
                        self.interface.console.print(f"\n[bold cyan]Portfolio Bot:[/bold cyan] {response}\n")
                    continue
                if not user_input.strip():
                    continue

                response = self.interface.show_loading(
                    "[bold cyan]Portfolio Bot is thinking...[/bold cyan]",
                    self.chatbot.chat,
                    user_input,
                )
                if response:
                    self.interface.console.print(f"\n[bold cyan]Portfolio Bot:[/bold cyan] {response}\n")
            except KeyboardInterrupt:
                self.interface.print_info("\nExiting chatbot...")
                break
            except Exception as error:
                self.interface.print_error(f"Error: {str(error)}")


def main():
    cli = TraderCLI()
    cli.run()
