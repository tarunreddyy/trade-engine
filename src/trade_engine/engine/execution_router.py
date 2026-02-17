from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from trade_engine.brokers.base_broker import BaseBroker


class ExecutionRouter:
    """Routes orders to paper simulator or broker adapter."""

    def __init__(self, mode: str = "paper", broker: Optional[BaseBroker] = None):
        self.mode = (mode or "paper").lower()
        self.broker = broker
        self._last_order_at: Dict[str, datetime] = {}
        self._duplicate_window = timedelta(seconds=20)

    def set_mode(self, mode: str):
        self.mode = (mode or "paper").lower()

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        if "." in symbol:
            return symbol.split(".")[0]
        return symbol

    def _is_duplicate(self, key: str) -> bool:
        now = datetime.utcnow()
        prev = self._last_order_at.get(key)
        if prev and (now - prev) <= self._duplicate_window:
            return True
        self._last_order_at[key] = now
        return False

    def route_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        exchange: str = "NSE",
        segment: str = "CASH",
    ) -> Dict[str, Any]:
        side = side.upper()
        dedupe_key = f"{symbol}:{side}"
        if self._is_duplicate(dedupe_key):
            return {
                "status": "SKIPPED",
                "reason": "duplicate_window",
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": round(price, 2),
            }

        if self.mode == "paper":
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
            return {
                "status": "SENT",
                "mode": "live",
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": round(price, 2),
                "broker_response": response,
            }

        return {
            "status": "REJECTED",
            "reason": f"unknown_mode:{self.mode}",
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
        }


