import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from rich.columns import Columns
from rich.console import Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from trade_engine.brokers.base_broker import BaseBroker
from trade_engine.core.event_bus import EventBus
from trade_engine.core.market_data_service import MarketDataService
from trade_engine.config.trading_config import (
    get_live_dashboard_control_file,
    get_live_dashboard_port,
    get_live_dashboard_state_file,
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
from trade_engine.web.live_dashboard import LiveDashboardServer, read_dashboard_controls, write_dashboard_state


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
        broker: BaseBroker | None = None,
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
        self.market_data = MarketDataService()
        self.dashboard_state_file = get_live_dashboard_state_file()
        self.dashboard_control_file = get_live_dashboard_control_file()
        self.dashboard_port = get_live_dashboard_port()
        self.dashboard_server: LiveDashboardServer | None = None
        self.event_bus = EventBus()
        self.metrics = RuntimeMetrics()
        self.event_bus.subscribe("*", lambda evt: self.metrics.on_event(evt.event_type))

        self.cash = initial_capital
        self.positions: dict[str, PositionState] = {}
        self.realized_pnl = 0.0
        self.event_log: list[str] = []
        self.equity_history: list[float] = []
        self.runtime_watchlist: list[str] = []
        self._latest_snapshots: list[dict[str, Any]] = []
        self._latest_equity: float = initial_capital
        self._command_buffer: str = ""
        self._symbol_controls: dict[str, dict[str, bool]] = {}
        self.signal_triggers: list[dict[str, Any]] = []

    @staticmethod
    def _signal_text(signal: int) -> str:
        if signal == 1:
            return "[green]BUY[/green]"
        if signal == -1:
            return "[red]SELL[/red]"
        return "[yellow]HOLD[/yellow]"

    @staticmethod
    def _sparkline(values: list[float], width: int = 32) -> str:
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

    @staticmethod
    def _signal_label(signal: int) -> str:
        if signal == 1:
            return "BUY"
        if signal == -1:
            return "SELL"
        return "HOLD"

    def _load_symbol_controls(self, symbols: list[str]) -> dict[str, dict[str, bool]]:
        payload = read_dashboard_controls(self.dashboard_control_file)
        symbol_controls = payload.get("symbol_controls", {}) if isinstance(payload, dict) else {}
        resolved: dict[str, dict[str, bool]] = {}
        for symbol in symbols:
            row = symbol_controls.get(symbol, {}) if isinstance(symbol_controls, dict) else {}
            resolved[symbol] = {
                "buy": bool(row.get("buy", True)),
                "sell": bool(row.get("sell", True)),
            }
        self._symbol_controls = resolved
        return resolved

    def _is_symbol_side_enabled(self, symbol: str, side: str) -> bool:
        controls = self._symbol_controls.get(symbol, {"buy": True, "sell": True})
        return bool(controls.get(side.lower(), True))

    def _append_trigger(self, symbol: str, signal: int, price: float | None, action: str):
        if signal not in {1, -1}:
            return
        self.signal_triggers.insert(
            0,
            {
                "timestamp": datetime.utcnow().strftime("%H:%M:%S"),
                "symbol": symbol,
                "signal_text": self._signal_label(signal),
                "price": None if price is None else round(float(price), 4),
                "action": action,
            },
        )
        self.signal_triggers = self.signal_triggers[:200]

    def _start_dashboard_server(self, open_browser: bool = False) -> str:
        if self.dashboard_server:
            return self.dashboard_server.url
        self.dashboard_server = LiveDashboardServer(
            host="127.0.0.1",
            port=self.dashboard_port,
            state_file=self.dashboard_state_file,
            control_file=self.dashboard_control_file,
        )
        return self.dashboard_server.start(open_browser=open_browser)

    def _build_dashboard_payload(
        self,
        strategy_name: str,
        snapshots: list[dict[str, Any]],
        session_started_at: str,
    ) -> dict[str, Any]:
        latest_prices = {row["symbol"]: row.get("price") for row in snapshots}
        positions: list[dict[str, Any]] = []
        for symbol, position in self.positions.items():
            market_price = latest_prices.get(symbol, position.entry_price)
            if market_price is None:
                market_price = position.entry_price
            if position.side == "LONG":
                upnl = (float(market_price) - position.entry_price) * position.quantity
            else:
                upnl = (position.entry_price - float(market_price)) * position.quantity
            positions.append(
                {
                    "symbol": symbol,
                    "side": position.side,
                    "quantity": position.quantity,
                    "entry_price": round(position.entry_price, 4),
                    "market_price": round(float(market_price), 4),
                    "unrealized_pnl": round(upnl, 2),
                }
            )

        watchlist: list[dict[str, Any]] = []
        for row in snapshots:
            symbol = row["symbol"]
            controls = self._symbol_controls.get(symbol, {"buy": True, "sell": True})
            watchlist.append(
                {
                    "symbol": symbol,
                    "price": None if row.get("price") is None else round(float(row["price"]), 4),
                    "change_pct": None if row.get("change_pct") is None else round(float(row["change_pct"]), 4),
                    "signal": int(row.get("signal", 0)),
                    "signal_text": self._signal_label(int(row.get("signal", 0))),
                    "buy_enabled": bool(controls.get("buy", True)),
                    "sell_enabled": bool(controls.get("sell", True)),
                }
            )

        session_summary = self.router.journal.get_session_summary(since_iso=session_started_at, limit=30)
        try:
            indices = self.market_data.get_indices_snapshot()
        except Exception:
            indices = []
        try:
            fno = self.market_data.get_fno_snapshot()
        except Exception:
            fno = []
        return {
            "strategy_name": strategy_name,
            "mode": self.router.mode,
            "cash": round(self.cash, 2),
            "equity": round(self._latest_equity, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "positions": positions,
            "watchlist": watchlist,
            "signal_triggers": self.signal_triggers[:80],
            "open_orders": session_summary.get("open_rows", []),
            "closed_orders": session_summary.get("closed_rows", []),
            "session": {
                "started_at": session_started_at,
                "total_orders": session_summary.get("total_orders", 0),
                "open_orders": session_summary.get("open_orders", 0),
                "closed_orders": session_summary.get("closed_orders", 0),
            },
            "indices": indices,
            "fno": fno,
        }

    def _export_dashboard_state(
        self,
        strategy_name: str,
        snapshots: list[dict[str, Any]],
        session_started_at: str,
    ):
        payload = self._build_dashboard_payload(
            strategy_name=strategy_name,
            snapshots=snapshots,
            session_started_at=session_started_at,
        )
        write_dashboard_state(self.dashboard_state_file, payload)

    def _serialize_state(self, symbols: list[str]) -> dict[str, Any]:
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

    def save_runtime_state(self, symbols: list[str] | None = None) -> bool:
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

            restored_positions: dict[str, PositionState] = {}
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

    def get_portfolio_state(self, latest_prices: dict[str, float] | None = None) -> dict[str, Any]:
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

    def _build_snapshot(self, strategy, symbols: list[str], period: str, interval: str) -> list[dict[str, Any]]:
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

    def _process_signals(self, snapshots: list[dict[str, Any]]):
        if self.risk_engine.daily_loss_breached(self.realized_pnl):
            self._log_event("Daily max-loss breached. New entries are disabled.")
            return

        current_exposure = 0.0
        for snapshot in snapshots:
            if snapshot["symbol"] in self.positions and snapshot["price"] is not None:
                current_exposure += self.positions[snapshot["symbol"]].quantity * snapshot["price"]

        for snapshot in snapshots:
            symbol = snapshot["symbol"]
            signal = int(snapshot.get("signal", 0))
            price = snapshot.get("price")
            if price is None:
                continue

            current_position = self.positions.get(symbol)
            if current_position:
                if current_position.side == "LONG":
                    should_exit, reason = self.risk_engine.check_exit(current_position.entry_price, price)
                    if should_exit and self.risk_config.sell_enabled:
                        self._append_trigger(symbol, -1, price, reason)
                        self._exit_position(symbol, price, reason)
                        continue
                    if signal == -1 and self.risk_engine.is_signal_enabled(signal):
                        if self._is_symbol_side_enabled(symbol, "sell"):
                            self._append_trigger(symbol, signal, price, "STRATEGY_SELL")
                            self._exit_position(symbol, price, "STRATEGY_SELL")
                        else:
                            self._append_trigger(symbol, signal, price, "SELL_DISABLED")
                else:
                    should_exit, reason = self.risk_engine.check_exit_short(current_position.entry_price, price)
                    if should_exit and self.risk_config.buy_enabled:
                        self._append_trigger(symbol, 1, price, reason)
                        self._exit_position(symbol, price, reason)
                        continue
                    if signal == 1 and self.risk_engine.is_signal_enabled(signal):
                        if self._is_symbol_side_enabled(symbol, "buy"):
                            self._append_trigger(symbol, signal, price, "STRATEGY_BUY")
                            self._exit_position(symbol, price, "STRATEGY_BUY")
                        else:
                            self._append_trigger(symbol, signal, price, "BUY_DISABLED")
                continue

            if signal == 1 and self.risk_engine.is_signal_enabled(signal):
                if not self._is_symbol_side_enabled(symbol, "buy"):
                    self._append_trigger(symbol, signal, price, "BUY_DISABLED")
                    continue
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
                        self._append_trigger(symbol, signal, price, f"BUY_BLOCKED:{reason}")
                    continue
                self._append_trigger(symbol, signal, price, "BUY_EXECUTED")
                self._enter_position(symbol, qty, price, side="BUY")
                current_exposure += qty * price
            elif signal == -1 and self.risk_engine.is_signal_enabled(signal):
                if not self._is_symbol_side_enabled(symbol, "sell"):
                    self._append_trigger(symbol, signal, price, "SELL_DISABLED")
                    continue
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
                        self._append_trigger(symbol, signal, price, f"SELL_BLOCKED:{reason}")
                    continue
                self._append_trigger(symbol, signal, price, "SELL_EXECUTED")
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

    def _compute_equity(self, snapshots: list[dict[str, Any]]) -> float:
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

    def _update_runtime_metrics(self, snapshots: list[dict[str, Any]]):
        equity = self._compute_equity(snapshots)
        self._latest_equity = equity
        self.equity_history.append(equity)
        self.equity_history = self.equity_history[-200:]
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

    def _build_dashboard(self, strategy_name: str, snapshots: list[dict[str, Any]], seconds_to_refresh: int) -> Group:
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
        watch.add_column("BuyEn")
        watch.add_column("SellEn")
        watch.add_column("Side")
        watch.add_column("Position", justify="right")
        watch.add_column("Entry", justify="right")
        watch.add_column("Unrealized", justify="right")
        for row in snapshots:
            symbol = row["symbol"]
            position = self.positions.get(symbol)
            controls = self._symbol_controls.get(symbol, {"buy": True, "sell": True})
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
                "ON" if controls.get("buy", True) else "OFF",
                "ON" if controls.get("sell", True) else "OFF",
                position.side if position else "-",
                str(position.quantity) if position else "-",
                f"{position.entry_price:.2f}" if position else "-",
                upnl_text,
            )

        spark = self._sparkline(self.equity_history)

        summary = Table(title="Account Summary", show_header=True, header_style="bold green")
        summary.add_column("Cash")
        summary.add_column("Equity")
        summary.add_column("Realized PnL")
        summary.add_column("Open Positions")
        summary.add_row(
            f"{self.cash:,.2f}",
            f"{self._latest_equity:,.2f}",
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
        command_panel = Panel(
            (
                "[bold white]Slash Commands:[/bold white] "
                "/buy on|off, /sell on|off, /sl <pct>, /tp <pct>, /risk <pct>, /maxpos <pct>, /mode paper|live, "
                "/kill on|off, /hours on|off, /maxorders <n>, /add <SYM>, /remove <SYM>, /clearstate, /help, /quit\n"
                "[dim]Per-symbol BUY/SELL toggles are controlled from web dashboard checkboxes.[/dim]\n"
                "[dim]Shortcuts: /b /s /r /m /q /h /ls /pt /mp /ko /mh /mo /a /rm /cs[/dim]\n"
                f"[bold yellow]Input[/bold yellow]: [cyan]{self._command_buffer}[/cyan]  "
                f"[dim](next refresh in {seconds_to_refresh}s)[/dim]"
            ),
            border_style="white",
            title="Command Console",
        )

        return Group(
            Columns(
                [
                    Panel(metrics, border_style="magenta"),
                    Panel(summary, border_style="green"),
                ]
            ),
            spark_panel,
            Panel(watch, border_style="cyan"),
            Panel(events, border_style="yellow"),
            command_panel,
        )

    def _poll_command_nonblocking(self) -> str | None:
        if os.name != "nt":
            return None
        try:
            import msvcrt
        except Exception:
            return None

        while msvcrt.kbhit():
            character = msvcrt.getwch()
            if character in {"\r", "\n"}:
                command = self._command_buffer.strip()
                self._command_buffer = ""
                return command
            if character in {"\b", "\x08"}:
                self._command_buffer = self._command_buffer[:-1]
                continue
            if character == "\x03":
                raise KeyboardInterrupt
            if character.isprintable():
                self._command_buffer += character
        return None

    def _apply_command(self, cmd: str, symbols: list[str]) -> bool:
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
        aliases = {
            "b": "buy",
            "s": "sell",
            "r": "risk",
            "m": "mode",
            "q": "quit",
            "h": "help",
            "ls": "sl",
            "pt": "tp",
            "mp": "maxpos",
            "ko": "kill",
            "mh": "hours",
            "mo": "maxorders",
            "a": "add",
            "rm": "remove",
            "cs": "clearstate",
        }
        key = aliases.get(key, key)
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
        symbols: list[str],
        refresh_seconds: int = 15,
        period: str = "5d",
        interval: str = "5m",
        execution_mode: str = "paper",
        resume_session: bool | None = None,
        launch_web_dashboard: bool = True,
        open_dashboard_browser: bool = True,
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
        self._command_buffer = ""
        self._latest_snapshots = []
        self.signal_triggers = []
        session_started_at = datetime.utcnow().isoformat()

        if launch_web_dashboard:
            dashboard_url = self._start_dashboard_server(open_browser=open_dashboard_browser)
            self._log_event(f"Web dashboard: {dashboard_url}")

        running = True
        next_refresh = time.monotonic()

        try:
            with Live(console=self.interface.console, screen=True, auto_refresh=False) as live:
                while running:
                    now = time.monotonic()

                    if not self._latest_snapshots or now >= next_refresh:
                        self._load_symbol_controls(symbols)
                        snapshots = self._build_snapshot(strategy, symbols, period=period, interval=interval)
                        self._latest_snapshots = snapshots
                        self._process_signals(snapshots)
                        if self.router.mode == "live":
                            reconciliation = self.router.reconcile_order_statuses()
                            if reconciliation.get("updated", 0) > 0:
                                self._log_event(
                                    f"Reconciled {reconciliation['updated']}/{reconciliation['checked']} live orders."
                                )
                        self._update_runtime_metrics(snapshots)
                        self._export_dashboard_state(
                            strategy_name=strategy_name,
                            snapshots=snapshots,
                            session_started_at=session_started_at,
                        )
                        self.save_runtime_state(symbols)
                        next_refresh = now + max(1, refresh_seconds)

                    command = self._poll_command_nonblocking()
                    if command is not None:
                        running = self._apply_command(command, symbols)
                        self.save_runtime_state(symbols)
                        if not running:
                            break

                    seconds_to_refresh = max(0, int(next_refresh - now))
                    live.update(
                        self._build_dashboard(
                            strategy_name=strategy_name,
                            snapshots=self._latest_snapshots,
                            seconds_to_refresh=seconds_to_refresh,
                        ),
                        refresh=True,
                    )
                    time.sleep(0.05)
        finally:
            self.save_runtime_state(symbols)
            if self.dashboard_server:
                self.dashboard_server.stop()
                self.dashboard_server = None


