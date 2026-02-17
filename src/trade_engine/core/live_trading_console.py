import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict, List, Optional

from rich.columns import Columns
from rich.panel import Panel
from rich.table import Table

from trade_engine.brokers.base_broker import BaseBroker
from trade_engine.core.event_bus import EventBus
from trade_engine.config.trading_config import (
    get_kill_switch_enabled,
    get_live_auto_resume_session,
    get_live_market_hours_only,
    get_live_max_orders_per_day,
    get_live_session_state_file,
)
from trade_engine.engine.execution_router import ExecutionRouter
from trade_engine.engine.observability import RuntimeMetrics
from trade_engine.engine.position_sizer import PositionSizer
from trade_engine.engine.risk_engine import RiskConfig, RiskEngine
from trade_engine.engine.session_state_store import SessionStateStore


@dataclass
class PositionState:
    symbol: str
    quantity: int
    entry_price: float
    side: str
    opened_at: str


class LiveTradingConsole:
    """Real-time CLI console for strategy-driven execution (paper/live)."""

    def __init__(
        self,
        interface,
        broker: Optional[BaseBroker] = None,
        initial_capital: float = 100000.0,
    ):
        self.interface = interface
        self.broker = broker
        self.risk_config = RiskConfig(initial_capital=initial_capital)
        self.risk_config.kill_switch_enabled = get_kill_switch_enabled()
        self.risk_config.market_hours_only = get_live_market_hours_only()
        self.risk_config.max_orders_per_day = get_live_max_orders_per_day()
        self.risk_engine = RiskEngine(self.risk_config)
        self.position_sizer = PositionSizer()
        self.router = ExecutionRouter(mode="paper", broker=self.broker, risk_engine=self.risk_engine)
        self.state_store = SessionStateStore(get_live_session_state_file())
        self.event_bus = EventBus()
        self.metrics = RuntimeMetrics()
        self.event_bus.subscribe("*", lambda evt: self.metrics.on_event(evt.event_type))

        self.cash = initial_capital
        self.positions: Dict[str, PositionState] = {}
        self.realized_pnl = 0.0
        self.event_log: List[str] = []
        self.equity_history: List[float] = []
        self.runtime_watchlist: List[str] = []

    @staticmethod
    def _signal_text(signal: int) -> str:
        if signal == 1:
            return "[green]BUY[/green]"
        if signal == -1:
            return "[red]SELL[/red]"
        return "[yellow]HOLD[/yellow]"

    @staticmethod
    def _sparkline(values: List[float], width: int = 32) -> str:
        if not values:
            return ""
        blocks = "._-:=+*#%@"
        if len(values) > width:
            values = values[-width:]
        v_min, v_max = min(values), max(values)
        if v_max == v_min:
            return blocks[0] * len(values)
        rendered = []
        for value in values:
            idx = int((value - v_min) / (v_max - v_min) * (len(blocks) - 1))
            rendered.append(blocks[idx])
        return "".join(rendered)

    def _log_event(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.event_log.append(f"[{timestamp}] {message}")
        self.event_log = self.event_log[-30:]
        self.event_bus.publish("log_event", {"message": message})

    def _serialize_state(self, symbols: List[str]) -> dict:
        return {
            "version": 1,
            "cash": self.cash,
            "realized_pnl": self.realized_pnl,
            "positions": [asdict(position) for position in self.positions.values()],
            "event_log": self.event_log[-80:],
            "equity_history": self.equity_history[-500:],
            "watchlist": list(symbols),
            "router_mode": self.router.mode,
            "risk_config": {
                "initial_capital": self.risk_config.initial_capital,
                "max_daily_loss_pct": self.risk_config.max_daily_loss_pct,
                "max_position_pct": self.risk_config.max_position_pct,
                "risk_per_trade_pct": self.risk_config.risk_per_trade_pct,
                "stop_loss_pct": self.risk_config.stop_loss_pct,
                "take_profit_pct": self.risk_config.take_profit_pct,
                "buy_enabled": self.risk_config.buy_enabled,
                "sell_enabled": self.risk_config.sell_enabled,
                "kill_switch_enabled": self.risk_config.kill_switch_enabled,
                "market_hours_only": self.risk_config.market_hours_only,
                "max_orders_per_day": self.risk_config.max_orders_per_day,
            },
        }

    def save_runtime_state(self, symbols: Optional[List[str]] = None) -> bool:
        symbols = symbols or self.runtime_watchlist
        return self.state_store.save_state(self._serialize_state(symbols))

    def try_restore_saved_state(self) -> bool:
        loaded = self.state_store.load_state()
        if loaded:
            return self._restore_state(loaded)
        return False

    def _restore_state(self, state: dict) -> bool:
        try:
            self.cash = float(state.get("cash", self.cash))
            self.realized_pnl = float(state.get("realized_pnl", self.realized_pnl))

            restored_positions: Dict[str, PositionState] = {}
            for entry in state.get("positions", []):
                symbol = str(entry.get("symbol", "")).upper()
                if not symbol:
                    continue
                restored_positions[symbol] = PositionState(
                    symbol=symbol,
                    quantity=int(entry.get("quantity", 0)),
                    entry_price=float(entry.get("entry_price", 0.0)),
                    side=str(entry.get("side", "LONG")).upper(),
                    opened_at=str(entry.get("opened_at", "")),
                )
            self.positions = restored_positions

            self.event_log = [str(item) for item in state.get("event_log", [])][-80:]
            self.equity_history = [float(item) for item in state.get("equity_history", [])][-500:]

            risk = state.get("risk_config", {})
            self.risk_config.max_daily_loss_pct = float(risk.get("max_daily_loss_pct", self.risk_config.max_daily_loss_pct))
            self.risk_config.max_position_pct = float(risk.get("max_position_pct", self.risk_config.max_position_pct))
            self.risk_config.risk_per_trade_pct = float(risk.get("risk_per_trade_pct", self.risk_config.risk_per_trade_pct))
            self.risk_config.stop_loss_pct = float(risk.get("stop_loss_pct", self.risk_config.stop_loss_pct))
            self.risk_config.take_profit_pct = float(risk.get("take_profit_pct", self.risk_config.take_profit_pct))
            self.risk_config.buy_enabled = bool(risk.get("buy_enabled", self.risk_config.buy_enabled))
            self.risk_config.sell_enabled = bool(risk.get("sell_enabled", self.risk_config.sell_enabled))
            self.risk_config.kill_switch_enabled = bool(
                risk.get("kill_switch_enabled", self.risk_config.kill_switch_enabled)
            )
            self.risk_config.market_hours_only = bool(
                risk.get("market_hours_only", self.risk_config.market_hours_only)
            )
            self.risk_config.max_orders_per_day = int(
                risk.get("max_orders_per_day", self.risk_config.max_orders_per_day)
            )

            self.runtime_watchlist = [
                str(item).upper() for item in state.get("watchlist", []) if str(item).strip()
            ]
            self._log_event("Session restored from saved state.")
            return True
        except Exception:
            return False

    def get_portfolio_state(self, latest_prices: Optional[Dict[str, float]] = None) -> dict:
        latest_prices = latest_prices or {}
        holdings = []
        total_holdings_value = 0.0
        for symbol, pos in self.positions.items():
            price = latest_prices.get(symbol, pos.entry_price)
            if pos.side == "LONG":
                market_value = pos.quantity * price
            else:
                market_value = -pos.quantity * price
            total_holdings_value += market_value
            holdings.append(
                {
                    "symbol": symbol,
                    "quantity": pos.quantity,
                    "entry_price": pos.entry_price,
                    "side": pos.side,
                    "market_price": round(price, 4),
                    "market_value": round(market_value, 2),
                }
            )
        equity = self.cash + total_holdings_value
        return {
            "cash": round(self.cash, 2),
            "equity": round(equity, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "positions": holdings,
        }

    def _build_snapshot(self, strategy, symbols: List[str], period: str, interval: str):
        import yfinance as yf

        snapshots = []
        for symbol in symbols:
            try:
                df = yf.download(
                    symbol,
                    period=period,
                    interval=interval,
                    progress=False,
                    auto_adjust=False,
                    threads=False,
                )
                if df is None or df.empty:
                    snapshots.append({"symbol": symbol, "price": None, "signal": 0, "change_pct": None})
                    continue
                if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
                    df.columns = [c[0] for c in df.columns]

                analyzed = strategy.combine_signals(df) if hasattr(strategy, "combine_signals") else strategy.calculate_signals(df)
                latest = analyzed.iloc[-1]
                prev_close = float(analyzed["Close"].iloc[-2]) if len(analyzed) > 1 else float(latest["Close"])
                close = float(latest["Close"])
                change_pct = ((close - prev_close) / prev_close * 100) if prev_close else 0.0

                snapshots.append(
                    {
                        "symbol": symbol,
                        "price": close,
                        "signal": int(latest.get("signal", 0)),
                        "change_pct": change_pct,
                    }
                )
            except Exception as exc:
                self._log_event(f"{symbol}: data error ({exc})")
                snapshots.append({"symbol": symbol, "price": None, "signal": 0, "change_pct": None})
        return snapshots

    def _process_signals(self, snapshots: List[dict]):
        if self.risk_engine.daily_loss_breached(self.realized_pnl):
            self._log_event("Daily max-loss breached. New entries are disabled.")
            return

        current_exposure = 0.0
        for snapshot in snapshots:
            if snapshot["symbol"] in self.positions and snapshot["price"] is not None:
                current_exposure += self.positions[snapshot["symbol"]].quantity * snapshot["price"]

        for snapshot in snapshots:
            symbol = snapshot["symbol"]
            signal = snapshot["signal"]
            price = snapshot["price"]
            if price is None:
                continue

            current_position = self.positions.get(symbol)
            if current_position:
                if current_position.side == "LONG":
                    should_exit, reason = self.risk_engine.check_exit(current_position.entry_price, price)
                    if should_exit and self.risk_config.sell_enabled:
                        self._exit_position(symbol, price, reason)
                        continue
                    if signal == -1 and self.risk_engine.is_signal_enabled(signal):
                        self._exit_position(symbol, price, "STRATEGY_SELL")
                else:
                    should_exit, reason = self.risk_engine.check_exit_short(current_position.entry_price, price)
                    if should_exit and self.risk_config.buy_enabled:
                        self._exit_position(symbol, price, reason)
                        continue
                    if signal == 1 and self.risk_engine.is_signal_enabled(signal):
                        self._exit_position(symbol, price, "STRATEGY_BUY")
                continue

            if signal == 1 and self.risk_engine.is_signal_enabled(signal):
                qty = self.position_sizer.calculate_quantity(
                    cash=self.cash,
                    price=price,
                    risk_per_trade_pct=self.risk_config.risk_per_trade_pct,
                    stop_loss_pct=self.risk_config.stop_loss_pct,
                    max_position_pct=self.risk_config.max_position_pct,
                    capital_base=self.risk_config.initial_capital,
                )
                allowed, reason = self.risk_engine.can_open_position(
                    cash=self.cash,
                    current_exposure=current_exposure,
                    entry_price=price,
                    quantity=qty,
                )
                if not allowed:
                    if qty > 0:
                        self._log_event(f"{symbol}: BUY blocked ({reason})")
                    continue
                self._enter_position(symbol, qty, price, side="BUY")
                current_exposure += qty * price
            elif signal == -1 and self.risk_engine.is_signal_enabled(signal):
                qty = self.position_sizer.calculate_quantity(
                    cash=self.cash,
                    price=price,
                    risk_per_trade_pct=self.risk_config.risk_per_trade_pct,
                    stop_loss_pct=self.risk_config.stop_loss_pct,
                    max_position_pct=self.risk_config.max_position_pct,
                    capital_base=self.risk_config.initial_capital,
                )
                allowed, reason = self.risk_engine.can_open_position(
                    cash=max(self.cash, self.risk_config.initial_capital),
                    current_exposure=current_exposure,
                    entry_price=price,
                    quantity=qty,
                )
                if not allowed:
                    if qty > 0:
                        self._log_event(f"{symbol}: SHORT blocked ({reason})")
                    continue
                self._enter_position(symbol, qty, price, side="SELL")
                current_exposure += qty * price

    def _enter_position(self, symbol: str, quantity: int, price: float, side: str):
        order = self.router.route_order(symbol=symbol, side=side, quantity=quantity, price=price)
        self.metrics.on_order(order.get("status", ""))
        if order["status"] in {"FILLED", "SENT"}:
            direction = "LONG" if side == "BUY" else "SHORT"
            if direction == "LONG":
                self.cash -= quantity * price
            else:
                self.cash += quantity * price
            self.positions[symbol] = PositionState(
                symbol=symbol,
                quantity=quantity,
                entry_price=price,
                side=direction,
                opened_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
            self._log_event(f"{symbol}: {side} {quantity} @ {price:.2f} [{order['status']}]")
            self.event_bus.publish(
                "order_placed",
                {
                    "symbol": symbol,
                    "side": side,
                    "quantity": quantity,
                    "price": price,
                    "status": order.get("status"),
                },
            )
        elif order["status"] != "SKIPPED":
            self._log_event(f"{symbol}: {side} rejected ({order.get('reason', 'unknown')})")
            self.event_bus.publish(
                "order_rejected",
                {"symbol": symbol, "side": side, "reason": order.get("reason", "unknown")},
            )

    def _exit_position(self, symbol: str, price: float, reason: str):
        position = self.positions.get(symbol)
        if not position:
            return
        exit_side = "SELL" if position.side == "LONG" else "BUY"
        order = self.router.route_order(
            symbol=symbol,
            side=exit_side,
            quantity=position.quantity,
            price=price,
            is_exit=True,
        )
        self.metrics.on_order(order.get("status", ""))
        if order["status"] in {"FILLED", "SENT"}:
            if position.side == "LONG":
                pnl = (price - position.entry_price) * position.quantity
                self.cash += position.quantity * price
            else:
                pnl = (position.entry_price - price) * position.quantity
                self.cash -= position.quantity * price
            self.realized_pnl += pnl
            self._log_event(
                f"{symbol}: {exit_side} {position.quantity} @ {price:.2f} [{reason}] "
                f"PnL={pnl:.2f} [{order['status']}]"
            )
            del self.positions[symbol]
            self.event_bus.publish(
                "position_closed",
                {"symbol": symbol, "side": exit_side, "pnl": pnl, "reason": reason},
            )
        elif order["status"] != "SKIPPED":
            self._log_event(f"{symbol}: SELL rejected ({order.get('reason', 'unknown')})")

    def execute_manual_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        reason: str = "MANUAL",
    ) -> dict:
        symbol = symbol.upper().strip()
        side = side.upper().strip()
        if side not in {"BUY", "SELL"}:
            return {"status": "REJECTED", "reason": "invalid_side"}
        if quantity <= 0 or price <= 0:
            return {"status": "REJECTED", "reason": "invalid_quantity_or_price"}

        position = self.positions.get(symbol)
        is_exit = bool(
            position and ((position.side == "LONG" and side == "SELL") or (position.side == "SHORT" and side == "BUY"))
        )
        order = self.router.route_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            is_exit=is_exit,
        )
        self.metrics.on_order(order.get("status", ""))
        if order.get("status") not in {"FILLED", "SENT"}:
            if order.get("status") != "SKIPPED":
                self._log_event(f"{symbol}: {side} rejected ({order.get('reason', 'unknown')})")
            return order

        realized_delta = 0.0

        if not position:
            if side == "BUY":
                self.cash -= quantity * price
                self.positions[symbol] = PositionState(
                    symbol=symbol,
                    quantity=quantity,
                    entry_price=price,
                    side="LONG",
                    opened_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                )
            else:
                self.cash += quantity * price
                self.positions[symbol] = PositionState(
                    symbol=symbol,
                    quantity=quantity,
                    entry_price=price,
                    side="SHORT",
                    opened_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                )
            self._log_event(f"{symbol}: {reason} {side} {quantity} @ {price:.2f}")
            return order

        if position.side == "LONG":
            if side == "BUY":
                new_qty = position.quantity + quantity
                weighted_avg = ((position.entry_price * position.quantity) + (price * quantity)) / max(new_qty, 1)
                self.cash -= quantity * price
                position.quantity = new_qty
                position.entry_price = weighted_avg
                self.positions[symbol] = position
            else:
                closing_qty = min(quantity, position.quantity)
                realized_delta = (price - position.entry_price) * closing_qty
                self.cash += closing_qty * price
                remaining = position.quantity - closing_qty
                self.realized_pnl += realized_delta
                if remaining > 0:
                    position.quantity = remaining
                    self.positions[symbol] = position
                else:
                    del self.positions[symbol]
                if quantity > closing_qty:
                    extra_short = quantity - closing_qty
                    self.cash += extra_short * price
                    self.positions[symbol] = PositionState(
                        symbol=symbol,
                        quantity=extra_short,
                        entry_price=price,
                        side="SHORT",
                        opened_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    )
        else:
            if side == "SELL":
                new_qty = position.quantity + quantity
                weighted_avg = ((position.entry_price * position.quantity) + (price * quantity)) / max(new_qty, 1)
                self.cash += quantity * price
                position.quantity = new_qty
                position.entry_price = weighted_avg
                self.positions[symbol] = position
            else:
                covering_qty = min(quantity, position.quantity)
                realized_delta = (position.entry_price - price) * covering_qty
                self.cash -= covering_qty * price
                remaining = position.quantity - covering_qty
                self.realized_pnl += realized_delta
                if remaining > 0:
                    position.quantity = remaining
                    self.positions[symbol] = position
                else:
                    del self.positions[symbol]
                if quantity > covering_qty:
                    extra_long = quantity - covering_qty
                    self.cash -= extra_long * price
                    self.positions[symbol] = PositionState(
                        symbol=symbol,
                        quantity=extra_long,
                        entry_price=price,
                        side="LONG",
                        opened_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    )

        if realized_delta != 0:
            self._log_event(
                f"{symbol}: {reason} {side} {quantity} @ {price:.2f} realized_pnl={realized_delta:.2f}"
            )
        else:
            self._log_event(f"{symbol}: {reason} {side} {quantity} @ {price:.2f}")
        return order

    def _compute_equity(self, snapshots: List[dict]) -> float:
        equity = self.cash
        latest_prices = {row["symbol"]: row["price"] for row in snapshots}
        for symbol, pos in self.positions.items():
            mark = latest_prices.get(symbol, pos.entry_price)
            if mark is not None:
                if pos.side == "LONG":
                    equity += pos.quantity * mark
                else:
                    equity -= pos.quantity * mark
        return equity

    def _render_dashboard(self, strategy_name: str, snapshots: List[dict]):
        metrics = Table(title="Runtime Controls", show_header=True, header_style="bold magenta")
        metrics.add_column("Mode")
        metrics.add_column("Buy")
        metrics.add_column("Sell")
        metrics.add_column("SL %")
        metrics.add_column("TP %")
        metrics.add_column("Risk/Trade %")
        metrics.add_column("Max Pos %")
        metrics.add_column("Kill")
        metrics.add_column("MktHours")
        metrics.add_column("Orders")
        metrics.add_row(
            self.router.mode.upper(),
            "ON" if self.risk_config.buy_enabled else "OFF",
            "ON" if self.risk_config.sell_enabled else "OFF",
            f"{self.risk_config.stop_loss_pct * 100:.2f}",
            f"{self.risk_config.take_profit_pct * 100:.2f}",
            f"{self.risk_config.risk_per_trade_pct * 100:.2f}",
            f"{self.risk_config.max_position_pct * 100:.2f}",
            "ON" if self.risk_config.kill_switch_enabled else "OFF",
            "ON" if self.risk_config.market_hours_only else "OFF",
            f"{self.router.orders_today}/{self.risk_config.max_orders_per_day}",
        )

        watch = Table(title=f"Watchlist - {strategy_name}", show_header=True, header_style="bold cyan")
        watch.add_column("Symbol")
        watch.add_column("Price", justify="right")
        watch.add_column("Chg %", justify="right")
        watch.add_column("Signal")
        watch.add_column("Side")
        watch.add_column("Position", justify="right")
        watch.add_column("Entry", justify="right")
        watch.add_column("Unrealized", justify="right")
        for row in snapshots:
            symbol = row["symbol"]
            position = self.positions.get(symbol)
            price = row["price"]
            change_pct = row["change_pct"]
            if position and price is not None:
                if position.side == "LONG":
                    upnl = (price - position.entry_price) * position.quantity
                else:
                    upnl = (position.entry_price - price) * position.quantity
                upnl_text = f"{upnl:.2f}"
            else:
                upnl_text = "-"
            watch.add_row(
                symbol,
                "-" if price is None else f"{price:.2f}",
                "-" if change_pct is None else f"{change_pct:.2f}",
                self._signal_text(row["signal"]),
                position.side if position else "-",
                str(position.quantity) if position else "-",
                f"{position.entry_price:.2f}" if position else "-",
                upnl_text,
            )

        equity = self._compute_equity(snapshots)
        self.equity_history.append(equity)
        self.equity_history = self.equity_history[-200:]
        spark = self._sparkline(self.equity_history)
        metrics_payload = self.metrics.snapshot(
            equity=equity,
            cash=self.cash,
            realized_pnl=self.realized_pnl,
            open_positions=len(self.positions),
            orders_today=self.router.orders_today,
            recent_events=self.event_log,
        )
        self.metrics.export(metrics_payload)
        self.event_bus.publish("runtime_snapshot", metrics_payload)

        summary = Table(title="Account Summary", show_header=True, header_style="bold green")
        summary.add_column("Cash")
        summary.add_column("Equity")
        summary.add_column("Realized PnL")
        summary.add_column("Open Positions")
        summary.add_row(
            f"{self.cash:,.2f}",
            f"{equity:,.2f}",
            f"{self.realized_pnl:,.2f}",
            str(len(self.positions)),
        )

        events = Table(title="Recent Events", show_header=False)
        events.add_column("Event")
        for event in reversed(self.event_log[-10:]):
            events.add_row(event)

        if not self.event_log:
            events.add_row("No events yet.")

        spark_panel = Panel(spark or "-", title="Equity Trend", border_style="blue")

        self.interface.clear_screen()
        self.interface.console.print(
            Columns(
                [
                    Panel(metrics, border_style="magenta"),
                    Panel(summary, border_style="green"),
                ]
            )
        )
        self.interface.console.print(spark_panel)
        self.interface.console.print(Panel(watch, border_style="cyan"))
        self.interface.console.print(Panel(events, border_style="yellow"))
        self.interface.console.print(
            "[bold white]Commands:[/bold white] "
            "buy on|off, sell on|off, sl <pct>, tp <pct>, risk <pct>, maxpos <pct>, mode paper|live, "
            "kill on|off, hours on|off, maxorders <n>, add <SYM>, remove <SYM>, clearstate, help, quit"
        )

    def _timed_command(self, timeout_seconds: int) -> str:
        if os.name == "nt":
            try:
                import msvcrt

                self.interface.console.print(
                    f"[bold yellow]Command (auto-continue in {timeout_seconds}s): [/bold yellow]",
                    end="",
                )
                buffer = ""
                end_at = time.time() + timeout_seconds
                while time.time() < end_at:
                    if msvcrt.kbhit():
                        char = msvcrt.getwche()
                        if char in ("\r", "\n"):
                            self.interface.console.print("")
                            return buffer.strip()
                        if char == "\x08":
                            buffer = buffer[:-1]
                            continue
                        buffer += char
                    time.sleep(0.05)
                self.interface.console.print("")
                return ""
            except Exception:
                pass
        return ""

    def _apply_command(self, cmd: str, symbols: List[str]) -> bool:
        if not cmd:
            return True
        normalized = cmd.strip()
        if normalized == "/":
            self._log_event(
                "Commands: /help, /buy on|off, /sell on|off, /sl <pct>, /tp <pct>, /risk <pct>, /maxpos <pct>, "
                "/mode paper|live, /kill on|off, /hours on|off, /maxorders <n>, /add <SYM>, /remove <SYM>, /quit"
            )
            return True

        tokens = normalized.split()
        if not tokens:
            return True

        key = tokens[0].lstrip("/").lower()
        if key == "quit":
            self._log_event("Stopping live console.")
            return False
        if key == "help":
            self._log_event("Use controls: buy/sell, sl/tp, risk/maxpos, mode, add/remove, clearstate, quit.")
            return True
        if key == "clearstate":
            if self.state_store.clear_state():
                self._log_event("Saved session state cleared.")
            else:
                self._log_event("Failed to clear saved session state.")
            return True
        if key in {"buy", "sell"} and len(tokens) > 1:
            enabled = tokens[1].lower() == "on"
            if key == "buy":
                self.risk_config.buy_enabled = enabled
                self._log_event(f"BUY execution set to {'ON' if enabled else 'OFF'}.")
            else:
                self.risk_config.sell_enabled = enabled
                self._log_event(f"SELL execution set to {'ON' if enabled else 'OFF'}.")
            return True
        if key in {"sl", "tp", "risk", "maxpos"} and len(tokens) > 1:
            try:
                pct = float(tokens[1]) / 100.0
                if key == "sl":
                    self.risk_config.stop_loss_pct = max(0.001, pct)
                    self._log_event(f"Stop-loss updated to {self.risk_config.stop_loss_pct * 100:.2f}%.")
                elif key == "tp":
                    self.risk_config.take_profit_pct = max(0.001, pct)
                    self._log_event(f"Take-profit updated to {self.risk_config.take_profit_pct * 100:.2f}%.")
                elif key == "risk":
                    self.risk_config.risk_per_trade_pct = max(0.001, pct)
                    self._log_event(f"Risk/trade updated to {self.risk_config.risk_per_trade_pct * 100:.2f}%.")
                elif key == "maxpos":
                    self.risk_config.max_position_pct = max(0.01, pct)
                    self._log_event(f"Max position updated to {self.risk_config.max_position_pct * 100:.2f}%.")
            except ValueError:
                self._log_event("Invalid percentage value.")
            return True
        if key == "kill" and len(tokens) > 1:
            enabled = tokens[1].lower() == "on"
            self.risk_config.kill_switch_enabled = enabled
            self._log_event(f"Kill switch set to {'ON' if enabled else 'OFF'}.")
            return True
        if key == "hours" and len(tokens) > 1:
            enabled = tokens[1].lower() == "on"
            self.risk_config.market_hours_only = enabled
            self._log_event(f"Market-hours guard set to {'ON' if enabled else 'OFF'}.")
            return True
        if key == "maxorders" and len(tokens) > 1:
            try:
                value = max(1, int(tokens[1]))
                self.risk_config.max_orders_per_day = value
                self._log_event(f"Max orders/day set to {value}.")
            except ValueError:
                self._log_event("Invalid max orders value.")
            return True
        if key == "mode" and len(tokens) > 1:
            mode = tokens[1].lower()
            if mode in {"paper", "live"}:
                self.router.set_mode(mode)
                self._log_event(f"Execution mode set to {mode.upper()}.")
            else:
                self._log_event("Invalid mode. Use 'paper' or 'live'.")
            return True
        if key == "add" and len(tokens) > 1:
            symbol = tokens[1].upper()
            if symbol not in symbols:
                symbols.append(symbol)
                self._log_event(f"Added {symbol} to watchlist.")
            return True
        if key == "remove" and len(tokens) > 1:
            symbol = tokens[1].upper()
            if symbol in symbols:
                symbols.remove(symbol)
                self._log_event(f"Removed {symbol} from watchlist.")
            return True

        self._log_event("Unknown command. Type '/' to list commands.")
        return True

    def run(
        self,
        strategy,
        strategy_name: str,
        symbols: List[str],
        refresh_seconds: int = 15,
        period: str = "5d",
        interval: str = "5m",
        execution_mode: str = "paper",
        resume_session: Optional[bool] = None,
    ):
        if resume_session is None:
            resume_session = get_live_auto_resume_session()

        symbols = [s.upper() for s in symbols if s.strip()]
        self.runtime_watchlist = list(symbols)

        if resume_session:
            loaded = self.state_store.load_state()
            if loaded and self._restore_state(loaded):
                if self.runtime_watchlist:
                    symbols = list(dict.fromkeys(symbols + self.runtime_watchlist))
                elif not symbols:
                    symbols = list(self.runtime_watchlist)
                self._log_event("Auto-resume enabled: previous state loaded.")

        self.router.set_mode(execution_mode)
        if not symbols:
            raise ValueError("At least one symbol is required to run live console.")

        self._log_event(f"Started console in {self.router.mode.upper()} mode.")
        running = True
        while running:
            snapshots = self._build_snapshot(strategy, symbols, period=period, interval=interval)
            self._process_signals(snapshots)
            if self.router.mode == "live":
                reconciliation = self.router.reconcile_order_statuses()
                if reconciliation.get("updated", 0) > 0:
                    self._log_event(
                        f"Reconciled {reconciliation['updated']}/{reconciliation['checked']} live orders."
                    )
            self._render_dashboard(strategy_name=strategy_name, snapshots=snapshots)
            self.save_runtime_state(symbols)
            cmd = self._timed_command(timeout_seconds=refresh_seconds)
            running = self._apply_command(cmd, symbols)

        self.save_runtime_state(symbols)


