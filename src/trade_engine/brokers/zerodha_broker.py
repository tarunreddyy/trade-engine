from __future__ import annotations

import csv
import hashlib
import io
import sys
import time
from datetime import datetime
from typing import Any
from urllib.parse import quote_plus

import requests

from trade_engine.brokers.base_broker import BaseBroker
from trade_engine.config.settings_store import get_setting, set_setting
from trade_engine.exception.exception import CustomException


class ZerodhaBroker(BaseBroker):
    """Zerodha Kite REST adapter with CLI-managed token lifecycle."""

    BASE_URL = "https://api.kite.trade"
    INSTRUMENTS_CACHE_TTL_SECONDS = 60 * 60 * 6

    def __init__(self):
        self.api_key = str(get_setting("broker.zerodha.api_key", "", str) or "").strip()
        self.api_secret = str(get_setting("broker.zerodha.api_secret", "", str) or "").strip()
        self.access_token = str(get_setting("broker.zerodha.access_token", "", str) or "").strip()
        self.request_token = str(get_setting("broker.zerodha.request_token", "", str) or "").strip()
        self._instruments_cache: list[dict[str, Any]] = []
        self._instruments_cache_ts = 0.0
        self._instruments_cache_scope = "ALL"

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        normalized = str(symbol or "").strip().upper()
        if normalized.endswith(".NS") or normalized.endswith(".BO"):
            normalized = normalized.rsplit(".", 1)[0]
        return normalized

    @staticmethod
    def _to_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None or value == "":
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _to_int(value: Any, default: int = 0) -> int:
        try:
            if value is None or value == "":
                return default
            return int(float(value))
        except (TypeError, ValueError):
            return default

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        auth_required: bool = True,
        expect_json: bool = True,
    ) -> Any:
        headers = {"X-Kite-Version": "3"}
        if auth_required:
            headers["Authorization"] = f"token {self.api_key}:{self.authenticate()}"

        url = f"{self.BASE_URL}{path}"
        try:
            response = requests.request(
                method=method.upper(),
                url=url,
                headers=headers,
                params=params,
                data=data,
                timeout=25,
            )
        except requests.RequestException as error:
            raise CustomException(f"Zerodha request failed for {path}: {error}", sys) from error

        if not expect_json:
            if response.status_code >= 400:
                raise CustomException(
                    f"Zerodha API error {response.status_code} on {path}: {response.text}",
                    sys,
                )
            return response.text

        try:
            payload = response.json()
        except ValueError as error:
            raise CustomException(f"Zerodha API returned non-JSON response on {path}.", sys) from error

        if response.status_code >= 400:
            detail = payload.get("message") if isinstance(payload, dict) else payload
            raise CustomException(
                f"Zerodha API error {response.status_code} on {path}: {detail}",
                sys,
            )

        if isinstance(payload, dict) and payload.get("status") == "error":
            detail = payload.get("message") or payload
            raise CustomException(f"Zerodha API returned error on {path}: {detail}", sys)

        if isinstance(payload, dict) and "data" in payload:
            return payload["data"]
        return payload

    def _exchange_request_token(self) -> str:
        if not (self.api_key and self.api_secret and self.request_token):
            raise CustomException(
                "Zerodha request token exchange requires api_key, api_secret, and request_token.",
                sys,
            )
        checksum_raw = f"{self.api_key}{self.request_token}{self.api_secret}"
        checksum = hashlib.sha256(checksum_raw.encode("utf-8")).hexdigest()
        data = {
            "api_key": self.api_key,
            "request_token": self.request_token,
            "checksum": checksum,
        }
        response = self._request("POST", "/session/token", data=data, auth_required=False)
        if not isinstance(response, dict):
            raise CustomException("Zerodha session token response is invalid.", sys)
        token = str(response.get("access_token", "")).strip()
        if not token:
            raise CustomException("Zerodha session token response is missing access_token.", sys)
        return token

    @staticmethod
    def _map_exchange(exchange: str, segment: str) -> str:
        exchange_upper = str(exchange or "NSE").strip().upper()
        segment_upper = str(segment or "CASH").strip().upper()
        if segment_upper in {"FUTURES", "FNO"} and exchange_upper == "NSE":
            return "NFO"
        return exchange_upper

    @staticmethod
    def _map_product(segment: str) -> str:
        segment_upper = str(segment or "CASH").strip().upper()
        if segment_upper in {"FUTURES", "FNO"}:
            return "NRML"
        return "CNC"

    def _quote_key(self, trading_symbol: str, exchange: str = "NSE", segment: str = "CASH") -> str:
        mapped_exchange = self._map_exchange(exchange, segment)
        mapped_symbol = self._normalize_symbol(trading_symbol)
        return f"{mapped_exchange}:{mapped_symbol}"

    def _load_instruments(self, exchange: str | None = None) -> list[dict[str, Any]]:
        cache_scope = str(exchange or "ALL").upper()
        now = time.time()
        if (
            self._instruments_cache
            and cache_scope == self._instruments_cache_scope
            and (now - self._instruments_cache_ts) < self.INSTRUMENTS_CACHE_TTL_SECONDS
        ):
            return self._instruments_cache

        path = "/instruments"
        if exchange:
            path = f"/instruments/{str(exchange).upper()}"
        csv_text = self._request("GET", path, auth_required=True, expect_json=False)
        if not isinstance(csv_text, str):
            raise CustomException("Unexpected instruments payload from Zerodha.", sys)
        reader = csv.DictReader(io.StringIO(csv_text))
        rows = [dict(row) for row in reader]
        self._instruments_cache = rows
        self._instruments_cache_ts = now
        self._instruments_cache_scope = cache_scope
        return rows

    def authenticate(self) -> str:
        if self.access_token:
            if not self.api_key:
                raise CustomException(
                    "Zerodha API key missing. Set `broker.zerodha.api_key` in CLI settings.",
                    sys,
                )
            return self.access_token

        if self.api_key and self.api_secret and self.request_token:
            token = self._exchange_request_token()
            self.access_token = token
            set_setting("broker.zerodha.access_token", token)
            return token

        if self.api_key:
            login_url = (
                "https://kite.zerodha.com/connect/login?v=3"
                f"&api_key={quote_plus(self.api_key)}"
            )
            raise CustomException(
                "Zerodha access token missing. Login at "
                f"{login_url} to get request_token, then set `broker.zerodha.request_token` in CLI settings.",
                sys,
            )

        raise CustomException(
            "Zerodha access token missing. Configure `broker.zerodha.access_token` "
            "(or api_key/api_secret/request_token) in CLI settings.",
            sys,
        )

    def place_order(
        self,
        trading_symbol: str,
        quantity: int,
        price: float,
        exchange: str = "NSE",
        segment: str = "CASH",
        transaction_type: str = "BUY",
    ) -> Any:
        order_type = "LIMIT" if price and float(price) > 0 else "MARKET"
        payload = {
            "tradingsymbol": self._normalize_symbol(trading_symbol),
            "exchange": self._map_exchange(exchange, segment),
            "transaction_type": str(transaction_type or "BUY").upper(),
            "order_type": order_type,
            "quantity": int(quantity),
            "product": self._map_product(segment),
            "validity": "DAY",
        }
        if order_type == "LIMIT":
            payload["price"] = float(price)
        response = self._request("POST", "/orders/regular", data=payload)
        return response

    def modify_order(
        self,
        order_id: str,
        quantity: int,
        price: float,
        segment: str = "CASH",
    ) -> Any:
        order_type = "LIMIT" if price and float(price) > 0 else "MARKET"
        payload: dict[str, Any] = {
            "quantity": int(quantity),
            "order_type": order_type,
            "validity": "DAY",
        }
        if order_type == "LIMIT":
            payload["price"] = float(price)
        return self._request("PUT", f"/orders/regular/{order_id}", data=payload)

    def cancel_order(self, order_id: str, segment: str = "CASH") -> Any:
        return self._request("DELETE", f"/orders/regular/{order_id}")

    def get_order_list(
        self,
        segment: str = "CASH",
        page: int = 0,
        page_size: int = 10,
    ) -> Any:
        response = self._request("GET", "/orders")
        rows = response if isinstance(response, list) else []
        start = max(0, int(page)) * max(1, int(page_size))
        end = start + max(1, int(page_size))
        return rows[start:end]

    def get_order_status(self, order_id: str, segment: str = "CASH") -> Any:
        details = self.get_order_details(order_id=order_id, segment=segment)
        if isinstance(details, dict):
            status = str(details.get("order_status") or details.get("status") or details.get("state") or "").upper()
            return {
                "order_status": status,
                "order_id": str(details.get("order_id") or order_id),
                "details": details,
            }
        return {"order_status": "", "order_id": order_id, "details": details}

    def get_order_details(self, order_id: str, segment: str = "CASH") -> Any:
        response = self._request("GET", f"/orders/{order_id}")
        if isinstance(response, list):
            history = response
            latest = history[-1] if history else {}
            if isinstance(latest, dict):
                latest_with_alias = dict(latest)
                latest_with_alias.setdefault("order_id", order_id)
                if "order_status" not in latest_with_alias and "status" in latest_with_alias:
                    latest_with_alias["order_status"] = latest_with_alias.get("status")
                latest_with_alias["history"] = history
                return latest_with_alias
            return {"order_id": order_id, "history": history}
        if isinstance(response, dict):
            details = dict(response)
            details.setdefault("order_id", order_id)
            if "order_status" not in details and "status" in details:
                details["order_status"] = details.get("status")
            return details
        return response

    def get_trades_details(
        self,
        order_id: str,
        segment: str = "CASH",
        page: int = 0,
        page_size: int = 10,
    ) -> Any:
        try:
            response = self._request("GET", f"/orders/{order_id}/trades")
        except CustomException:
            all_trades = self._request("GET", "/trades")
            if isinstance(all_trades, list):
                response = [row for row in all_trades if str(row.get("order_id", "")) == str(order_id)]
            else:
                response = []
        rows = response if isinstance(response, list) else []
        start = max(0, int(page)) * max(1, int(page_size))
        end = start + max(1, int(page_size))
        return rows[start:end]

    def get_portfolio(self) -> Any:
        return self._request("GET", "/portfolio/holdings")

    def get_positions(self, segment: str | None = None) -> Any:
        response = self._request("GET", "/portfolio/positions")
        if not isinstance(response, dict) or not segment:
            return response
        segment_upper = str(segment or "").upper()
        if segment_upper in {"FUTURES", "FNO"}:
            return response.get("net", [])
        if segment_upper == "CASH":
            return response.get("day", [])
        return response

    def get_quote(
        self,
        trading_symbol: str,
        exchange: str = "NSE",
        segment: str = "CASH",
    ) -> Any:
        quote_key = self._quote_key(trading_symbol=trading_symbol, exchange=exchange, segment=segment)
        response = self._request("GET", "/quote", params={"i": quote_key})
        row = response.get(quote_key, {}) if isinstance(response, dict) else {}
        ohlc = row.get("ohlc", {}) if isinstance(row.get("ohlc"), dict) else {}
        ltp = self._to_float(row.get("last_price"), 0.0)
        return {
            "source": "zerodha",
            "symbol": self._normalize_symbol(trading_symbol),
            "exchange": self._map_exchange(exchange, segment),
            "segment": str(segment or "CASH").upper(),
            "ltp": round(ltp, 4),
            "open": round(self._to_float(ohlc.get("open"), ltp), 4),
            "high": round(self._to_float(ohlc.get("high"), ltp), 4),
            "low": round(self._to_float(ohlc.get("low"), ltp), 4),
            "volume": self._to_int(row.get("volume"), 0),
            "change": round(self._to_float(row.get("net_change"), 0.0), 4),
            "change_pct": 0.0,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def get_ltp(
        self,
        trading_symbol: str,
        exchange: str = "NSE",
        segment: str = "CASH",
    ) -> Any:
        quote_key = self._quote_key(trading_symbol=trading_symbol, exchange=exchange, segment=segment)
        response = self._request("GET", "/quote/ltp", params={"i": quote_key})
        row = response.get(quote_key, {}) if isinstance(response, dict) else {}
        ltp = self._to_float(row.get("last_price"), 0.0)
        return {
            "source": "zerodha",
            "symbol": self._normalize_symbol(trading_symbol),
            "exchange": self._map_exchange(exchange, segment),
            "segment": str(segment or "CASH").upper(),
            "ltp": round(ltp, 4),
            "timestamp": datetime.utcnow().isoformat(),
        }

    def search_instrument(self, symbol: str, exchange: str | None = None) -> Any:
        query = self._normalize_symbol(symbol)
        if not query:
            return []
        exchange_upper = str(exchange or "").strip().upper()
        rows: list[dict[str, Any]] = []
        for instrument in self._load_instruments(exchange=exchange_upper or None):
            trading_symbol = str(instrument.get("tradingsymbol", "")).upper()
            name = str(instrument.get("name", "")).upper()
            row_exchange = str(instrument.get("exchange", "")).upper()
            if exchange_upper and row_exchange != exchange_upper:
                continue
            if query not in trading_symbol and query not in name:
                continue
            rows.append(
                {
                    "symbol": trading_symbol,
                    "exchange": row_exchange,
                    "segment": instrument.get("segment", ""),
                    "instrument_token": instrument.get("instrument_token", ""),
                    "name": instrument.get("name", ""),
                    "tick_size": instrument.get("tick_size", ""),
                    "lot_size": instrument.get("lot_size", ""),
                }
            )
            if len(rows) >= 25:
                break
        return rows
