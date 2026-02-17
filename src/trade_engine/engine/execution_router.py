from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional

from trade_engine.brokers.base_broker import BaseBroker
from trade_engine.engine.risk_engine import RiskEngine


class ExecutionRouter:
    """Routes orders to paper simulator or broker adapter with safety controls."""

    def __init__(self, mode: str = "paper", broker: Optional[BaseBroker] = None, risk_engine: Optional[RiskEngine] = None):
        self.mode = (mode or "paper").lower()
        self.broker = broker
        self.risk_engine = risk_engine
        self._last_order_at: Dict[str, datetime] = {}
        self._duplicate_window = timedelta(seconds=20)
        self._orders_today = 0
        self._orders_day: date = datetime.utcnow().date()

    @property
    def orders_today(self) -> int:
        self._reset_order_counter_if_new_day()
        return self._orders_today

    def set_mode(self, mode: str):
        selected = (mode or "paper").lower()
        self.mode = selected if selected in {"paper", "live"} else "paper"

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        if "." in symbol:
            return symbol.split(".")[0]
        return symbol

    def _reset_order_counter_if_new_day(self):
        today = datetime.utcnow().date()
        if today != self._orders_day:
            self._orders_day = today
            self._orders_today = 0

    def _is_duplicate(self, key: str) -> bool:
        now = datetime.utcnow()
        prev = self._last_order_at.get(key)
        if prev and (now - prev) <= self._duplicate_window:
            return True
        self._last_order_at[key] = now
        return False

    def _apply_risk_guard(self, side: str, is_exit: bool) -> Dict[str, Any]:
        self._reset_order_counter_if_new_day()
        if not self.risk_engine:
            return {}
        allowed, reason = self.risk_engine.pre_order_guard(
            mode=self.mode,
            orders_today=self._orders_today,
            is_exit=is_exit,
        )
        if allowed:
            return {}
        return {
            "status": "REJECTED",
            "reason": reason,
            "mode": self.mode,
            "side": side,
            "orders_today": self._orders_today,
        }

    def route_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        exchange: str = "NSE",
        segment: str = "CASH",
        is_exit: bool = False,
    ) -> Dict[str, Any]:
        side = side.upper()
        dedupe_key = f"{symbol}:{side}:{'EXIT' if is_exit else 'ENTRY'}"
        if self._is_duplicate(dedupe_key):
            return {
                "status": "SKIPPED",
                "reason": "duplicate_window",
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": round(price, 2),
            }

        blocked = self._apply_risk_guard(side=side, is_exit=is_exit)
        if blocked:
            blocked.update(
                {
                    "symbol": symbol,
                    "quantity": quantity,
                    "price": round(price, 2),
                }
            )
            return blocked

        if self.mode == "paper":
            self._orders_today += 1
            return {
                "status": "FILLED",
                "mode": "paper",
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": round(price, 2),
                "broker_order_id": None,
            }

        if self.mode == "live":
            if not self.broker:
                return {
                    "status": "REJECTED",
                    "reason": "broker_not_configured",
                    "symbol": symbol,
                    "side": side,
                    "quantity": quantity,
                }
            try:
                response = self.broker.place_order(
                    trading_symbol=self._normalize_symbol(symbol),
                    quantity=quantity,
                    price=price,
                    exchange=exchange,
                    segment=segment,
                    transaction_type=side,
                )
            except Exception as exc:
                return {
                    "status": "REJECTED",
                    "reason": f"broker_error:{exc}",
                    "symbol": symbol,
                    "side": side,
                    "quantity": quantity,
                }
            self._orders_today += 1
            return {
                "status": "SENT",
                "mode": "live",
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": round(price, 2),
                "broker_response": response,
                "orders_today": self._orders_today,
            }

        return {
            "status": "REJECTED",
            "reason": f"unknown_mode:{self.mode}",
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
        }
