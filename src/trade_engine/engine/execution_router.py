from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional

from trade_engine.brokers.base_broker import BaseBroker
from trade_engine.engine.order_journal import OrderJournal
from trade_engine.engine.risk_engine import RiskEngine


class ExecutionRouter:
    """Routes orders to paper simulator or broker adapter with safety controls and persistence."""

    FINAL_STATES = {"COMPLETE", "FILLED", "CANCELLED", "REJECTED", "FAILED"}

    def __init__(
        self,
        mode: str = "paper",
        broker: Optional[BaseBroker] = None,
        risk_engine: Optional[RiskEngine] = None,
        journal: Optional[OrderJournal] = None,
    ):
        self.mode = (mode or "paper").lower()
        self.broker = broker
        self.risk_engine = risk_engine
        self.journal = journal or OrderJournal()
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

    @staticmethod
    def _extract_broker_order_id(response: Any) -> str:
        if response is None:
            return ""
        if isinstance(response, dict):
            for key in ("groww_order_id", "order_id", "id"):
                value = response.get(key)
                if value:
                    return str(value)
            for value in response.values():
                nested = ExecutionRouter._extract_broker_order_id(value)
                if nested:
                    return nested
        if isinstance(response, list):
            for item in response:
                nested = ExecutionRouter._extract_broker_order_id(item)
                if nested:
                    return nested
        return ""

    @staticmethod
    def _extract_broker_status(response: Any) -> str:
        if response is None:
            return ""
        if isinstance(response, dict):
            for key in ("order_status", "status", "state"):
                value = response.get(key)
                if value:
                    return str(value).upper()
            for value in response.values():
                nested = ExecutionRouter._extract_broker_status(value)
                if nested:
                    return nested
        if isinstance(response, list):
            for item in response:
                nested = ExecutionRouter._extract_broker_status(item)
                if nested:
                    return nested
        return ""

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

    def _record_order(self, result: Dict[str, Any], is_exit: bool, broker_payload: Optional[Dict[str, Any]] = None) -> int:
        return self.journal.record_order(
            symbol=result.get("symbol", ""),
            side=result.get("side", ""),
            quantity=int(result.get("quantity", 0)),
            price=float(result.get("price", 0.0)),
            mode=result.get("mode", self.mode),
            status=result.get("status", "UNKNOWN"),
            reason=result.get("reason", ""),
            broker_order_id=result.get("broker_order_id", "") or "",
            broker_payload=broker_payload,
            is_exit=is_exit,
        )

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
            result = {
                "status": "SKIPPED",
                "reason": "duplicate_window",
                "mode": self.mode,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": round(price, 2),
            }
            result["journal_id"] = self._record_order(result, is_exit=is_exit)
            return result

        blocked = self._apply_risk_guard(side=side, is_exit=is_exit)
        if blocked:
            blocked.update({"symbol": symbol, "quantity": quantity, "price": round(price, 2)})
            blocked["journal_id"] = self._record_order(blocked, is_exit=is_exit)
            return blocked

        if self.mode == "paper":
            self._orders_today += 1
            result = {
                "status": "FILLED",
                "mode": "paper",
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": round(price, 2),
                "broker_order_id": "",
            }
            result["journal_id"] = self._record_order(result, is_exit=is_exit)
            return result

        if self.mode == "live":
            if not self.broker:
                result = {
                    "status": "REJECTED",
                    "reason": "broker_not_configured",
                    "mode": "live",
                    "symbol": symbol,
                    "side": side,
                    "quantity": quantity,
                    "price": round(price, 2),
                }
                result["journal_id"] = self._record_order(result, is_exit=is_exit)
                return result
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
                result = {
                    "status": "REJECTED",
                    "reason": f"broker_error:{exc}",
                    "mode": "live",
                    "symbol": symbol,
                    "side": side,
                    "quantity": quantity,
                    "price": round(price, 2),
                }
                result["journal_id"] = self._record_order(result, is_exit=is_exit)
                return result

            self._orders_today += 1
            broker_order_id = self._extract_broker_order_id(response)
            result = {
                "status": "SENT",
                "mode": "live",
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": round(price, 2),
                "broker_order_id": broker_order_id,
                "broker_response": response,
                "orders_today": self._orders_today,
            }
            result["journal_id"] = self._record_order(result, is_exit=is_exit, broker_payload=response if isinstance(response, dict) else {})
            return result

        result = {
            "status": "REJECTED",
            "reason": f"unknown_mode:{self.mode}",
            "mode": self.mode,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": round(price, 2),
        }
        result["journal_id"] = self._record_order(result, is_exit=is_exit)
        return result

    def reconcile_order_statuses(self) -> Dict[str, Any]:
        """Poll broker order status for open live orders and update journal."""
        if self.mode != "live" or not self.broker:
            return {"checked": 0, "updated": 0, "rows": []}

        rows = self.journal.get_open_live_orders(limit=200)
        updated_rows = []
        for row in rows:
            broker_order_id = row.get("broker_order_id", "")
            if not broker_order_id:
                continue
            try:
                status_response = self.broker.get_order_status(order_id=broker_order_id)
                broker_status = self._extract_broker_status(status_response)
                if not broker_status:
                    continue
                normalized = broker_status.upper()
                terminal = normalized in self.FINAL_STATES
                persisted = self.journal.update_order(
                    journal_id=row["id"],
                    status=normalized,
                    reason="reconciled",
                    broker_payload=status_response if isinstance(status_response, dict) else {},
                )
                if persisted:
                    updated_rows.append(
                        {
                            "journal_id": row["id"],
                            "broker_order_id": broker_order_id,
                            "status": normalized,
                            "terminal": terminal,
                        }
                    )
            except Exception:
                continue
        return {"checked": len(rows), "updated": len(updated_rows), "rows": updated_rows}
