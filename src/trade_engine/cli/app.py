import sys

from trade_engine.brokers.broker_factory import BrokerFactory
from trade_engine.cli.ai_advisor_menu import AIAdvisorMenu
from trade_engine.cli.interface import CLInterface
from trade_engine.cli.settings_menu import SettingsMenu
from trade_engine.cli.strategy_menu import StrategyMenu
from trade_engine.cli.visualization_menu import VisualizationMenu
from trade_engine.core.portfolio_chatbot import PortfolioChatbot
from trade_engine.core.vector_db_search import VectorDBSearch


class TraderCLI:
    def __init__(self):
        self.interface = CLInterface()
        self.settings_menu = SettingsMenu(self.interface)
        self._refresh_runtime_components(initial_boot=True)

    def _refresh_runtime_components(self, initial_boot: bool = False):
        self.broker = BrokerFactory.create_broker()
        self.vector_search = None
        self.chatbot = None
        self.viz_menu = VisualizationMenu(self.interface)
        self.strategy_menu = StrategyMenu(self.interface, broker=self.broker)
        self.ai_advisor_menu = AIAdvisorMenu(self.interface)
        if not initial_boot:
            self.interface.print_success("Runtime services refreshed with latest CLI settings.")

    def run(self):
        self.interface.clear_screen()
        self.interface.print_banner()
        self.interface.typing_effect("Welcome to TradeEngine CLI!", delay=0.03, style="bold green")
        self.interface.typing_effect("Use Settings to manage broker/API/runtime config.", delay=0.02, style="yellow")

        while True:
            try:
                main_menu = [
                    "Orders Management",
                    "Portfolio and Positions",
                    "Live Market Data",
                    "Search Instruments",
                    "AI Vector Search",
                    "Portfolio Chatbot",
                    "Visualize Stock",
                    "Trading Strategies",
                    "AI Strategy Advisor",
                    "Settings",
                    "Exit",
                ]
                choice = self.interface.show_menu(main_menu, "Main Menu")

                if choice == "Orders Management":
                    self.handle_orders_menu()
                elif choice == "Portfolio and Positions":
                    self.handle_portfolio_menu()
                elif choice == "Live Market Data":
                    self.handle_live_data_menu()
                elif choice == "Search Instruments":
                    self.handle_search_menu()
                elif choice == "AI Vector Search":
                    self.handle_vector_search_menu()
                elif choice == "Portfolio Chatbot":
                    self.handle_chatbot_menu()
                elif choice == "Visualize Stock":
                    self.viz_menu.show()
                elif choice == "Trading Strategies":
                    self.strategy_menu.show()
                elif choice == "AI Strategy Advisor":
                    self.ai_advisor_menu.show()
                elif choice == "Settings":
                    changed = self.settings_menu.show()
                    if changed:
                        self._refresh_runtime_components()
                elif choice == "Exit":
                    self.interface.typing_effect("Thank you for using TradeEngine CLI!", delay=0.02, style="bold cyan")
                    sys.exit(0)
            except KeyboardInterrupt:
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
            "Get Live Quote",
            "Get LTP (Last Traded Price)",
            "Side-by-Side Comparison",
            "Back to Main Menu",
        ]
        choice = self.interface.show_menu(menu_options, "Live Market Data")

        if choice == "Get Live Quote":
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
                user_input = self.interface.input_prompt("You: ", style="bold green")
                command = user_input.lower().strip()
                if command in {"exit", "quit", "back"}:
                    self.interface.print_info("Exiting chatbot...")
                    break
                if command == "reset":
                    self.chatbot.reset_conversation()
                    self.interface.print_success("Conversation reset!")
                    continue
                if command == "refresh":
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
