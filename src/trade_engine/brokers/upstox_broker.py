from __future__ import annotations

import gzip
import json
import sys
import time
from datetime import datetime
from typing import Any
from urllib.parse import quote_plus

import requests

from trade_engine.brokers.base_broker import BaseBroker
from trade_engine.config.settings_store import get_setting, set_setting
from trade_engine.exception.exception import CustomException


class UpstoxBroker(BaseBroker):
    """Upstox adapter backed by REST APIs with lazy token resolution."""

    BASE_URL = "https://api.upstox.com"
    INSTRUMENTS_URL = "https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz"
    INSTRUMENT_CACHE_TTL_SECONDS = 60 * 60 * 6

    def __init__(self):
        self.api_key = str(get_setting("broker.upstox.api_key", "", str) or "").strip()
        self.api_secret = str(get_setting("broker.upstox.api_secret", "", str) or "").strip()
        self.access_token = str(get_setting("broker.upstox.access_token", "", str) or "").strip()
        self.redirect_uri = str(get_setting("broker.upstox.redirect_uri", "", str) or "").strip()
        self.auth_code = str(get_setting("broker.upstox.auth_code", "", str) or "").strip()
        self._instrument_cache: list[dict[str, Any]] = []
        self._instrument_cache_ts = 0.0

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

    @staticmethod
    def _extract_payload_data(payload: Any) -> Any:
        if isinstance(payload, dict) and "data" in payload:
            return payload["data"]
        return payload

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        auth_required: bool = True,
    ) -> Any:
        headers = {"Accept": "application/json"}
        if json_body is not None:
            headers["Content-Type"] = "application/json"
        if auth_required:
            headers["Authorization"] = f"Bearer {self.authenticate()}"

        url = f"{self.BASE_URL}{path}"
        try:
            response = requests.request(
                method=method.upper(),
                url=url,
                headers=headers,
                params=params,
                json=json_body,
                data=data,
                timeout=25,
            )
        except requests.RequestException as error:
            raise CustomException(f"Upstox request failed for {path}: {error}", sys) from error

        payload: Any
        try:
            payload = response.json()
        except ValueError:
            payload = {"raw": response.text}

        if response.status_code >= 400:
            detail = payload.get("errors") if isinstance(payload, dict) else payload
            raise CustomException(
                f"Upstox API error {response.status_code} on {path}: {detail}",
                sys,
            )

        if isinstance(payload, dict) and payload.get("status") == "error":
            detail = payload.get("errors") or payload.get("message") or payload
            raise CustomException(f"Upstox API returned error on {path}: {detail}", sys)

        return payload

    def _exchange_auth_code(self) -> str:
        url = f"{self.BASE_URL}/v2/login/authorization/token"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        form_data = {
            "code": self.auth_code,
            "client_id": self.api_key,
            "client_secret": self.api_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }
        try:
            response = requests.post(url, headers=headers, data=form_data, timeout=25)
        except requests.RequestException as error:
            raise CustomException(f"Upstox token exchange failed: {error}", sys) from error

        try:
            payload = response.json()
        except ValueError as error:
            raise CustomException("Upstox token exchange returned non-JSON response.", sys) from error

        if response.status_code >= 400 or (isinstance(payload, dict) and payload.get("status") == "error"):
            detail = payload.get("errors") if isinstance(payload, dict) else payload
            raise CustomException(f"Upstox token exchange failed: {detail}", sys)

        data = self._extract_payload_data(payload)
        if not isinstance(data, dict):
            raise CustomException("Upstox token exchange returned invalid payload.", sys)
        token = str(data.get("access_token", "")).strip()
        if not token:
            raise CustomException("Upstox token exchange returned empty access token.", sys)
        return token

    def _load_instruments(self) -> list[dict[str, Any]]:
        if self._instrument_cache and (time.time() - self._instrument_cache_ts) < self.INSTRUMENT_CACHE_TTL_SECONDS:
            return self._instrument_cache

        try:
            response = requests.get(self.INSTRUMENTS_URL, timeout=45)
            response.raise_for_status()
        except requests.RequestException as error:
            raise CustomException(f"Unable to download Upstox instruments: {error}", sys) from error

        raw_content = response.content
        if self.INSTRUMENTS_URL.endswith(".gz"):
            try:
                raw_content = gzip.decompress(raw_content)
            except OSError as error:
                raise CustomException("Failed to decompress Upstox instrument dump.", sys) from error

        try:
            payload = json.loads(raw_content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise CustomException("Failed to parse Upstox instrument dump JSON.", sys) from error

        if not isinstance(payload, list):
            raise CustomException("Unexpected Upstox instruments payload format.", sys)

        self._instrument_cache = [row for row in payload if isinstance(row, dict)]
        self._instrument_cache_ts = time.time()
        return self._instrument_cache

    @staticmethod
    def _get_row_symbol(row: dict[str, Any]) -> str:
        return str(
            row.get("trading_symbol")
            or row.get("tradingsymbol")
            or row.get("symbol")
            or row.get("name")
            or ""
        ).upper()

    def _resolve_instrument_key(self, trading_symbol: str, exchange: str = "NSE", segment: str = "CASH") -> str:
        symbol = self._normalize_symbol(trading_symbol)
        exchange_upper = str(exchange or "NSE").strip().upper()
        segment_upper = str(segment or "CASH").strip().upper()

        if not symbol:
            raise CustomException("Trading symbol cannot be empty for Upstox.", sys)

        if segment_upper in {"FUTURES", "FNO"}:
            target_prefixes = {"NFO_FO", "NSE_FO", "BFO_FO", "MCX_FO"}
        elif exchange_upper == "BSE":
            target_prefixes = {"BSE_EQ"}
        else:
            target_prefixes = {"NSE_EQ"}

        instruments = self._load_instruments()
        for row in instruments:
            instrument_key = str(row.get("instrument_key", "")).upper()
            row_symbol = self._get_row_symbol(row)
            if "|" not in instrument_key:
                continue
            prefix = instrument_key.split("|", 1)[0]
            if target_prefixes and prefix not in target_prefixes:
                continue
            if row_symbol == symbol:
                return instrument_key

        for row in instruments:
            instrument_key = str(row.get("instrument_key", "")).upper()
            row_symbol = self._get_row_symbol(row)
            if "|" not in instrument_key:
                continue
            prefix = instrument_key.split("|", 1)[0]
            if target_prefixes and prefix not in target_prefixes:
                continue
            if symbol in row_symbol:
                return instrument_key

        raise CustomException(
            f"Upstox instrument key not found for symbol '{symbol}' ({exchange_upper}/{segment_upper}).",
            sys,
        )

    @staticmethod
    def _extract_quote_row(data: Any, instrument_key: str) -> dict[str, Any]:
        if isinstance(data, dict):
            if instrument_key in data and isinstance(data[instrument_key], dict):
                return data[instrument_key]
            if len(data) == 1:
                first_value = next(iter(data.values()))
                if isinstance(first_value, dict):
                    return first_value
            if any(k in data for k in ("ltp", "last_price", "last_traded_price")):
                return data
        return {}

    @classmethod
    def _extract_ltp(cls, row: dict[str, Any]) -> float:
        if "ltp" in row and isinstance(row.get("ltp"), dict):
            return cls._to_float(row.get("ltp", {}).get("ltp"))
        return cls._to_float(
            row.get("last_price")
            or row.get("last_traded_price")
            or row.get("ltp")
            or row.get("close"),
        )

    def authenticate(self) -> str:
        if self.access_token:
            return self.access_token

        can_exchange = all([self.api_key, self.api_secret, self.redirect_uri, self.auth_code])
        if can_exchange:
            token = self._exchange_auth_code()
            self.access_token = token
            set_setting("broker.upstox.access_token", token)
            return token

        if self.api_key and self.redirect_uri:
            login_url = (
                "https://api.upstox.com/v2/login/authorization/dialog"
                f"?response_type=code&client_id={quote_plus(self.api_key)}"
                f"&redirect_uri={quote_plus(self.redirect_uri)}"
            )
            raise CustomException(
                "Upstox access token missing. Generate authorization code from "
                f"{login_url} and set `broker.upstox.auth_code` in CLI settings.",
                sys,
            )

        raise CustomException(
            "Upstox access token missing. Configure `broker.upstox.access_token` "
            "(or api_key/api_secret/redirect_uri/auth_code) in CLI settings.",
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
        instrument_key = self._resolve_instrument_key(trading_symbol, exchange=exchange, segment=segment)
        order_type = "LIMIT" if price and float(price) > 0 else "MARKET"
        segment_upper = str(segment or "CASH").upper()
        payload = {
            "quantity": int(quantity),
            "product": "D" if segment_upper == "CASH" else "I",
            "validity": "DAY",
            "price": float(price) if order_type == "LIMIT" else 0.0,
            "order_type": order_type,
            "transaction_type": str(transaction_type or "BUY").upper(),
            "disclosed_quantity": 0,
            "trigger_price": 0.0,
            "is_amo": False,
            "instrument_token": instrument_key,
        }
        response = self._request("POST", "/v2/order/place", json_body=payload)
        return self._extract_payload_data(response)

    def modify_order(
        self,
        order_id: str,
        quantity: int,
        price: float,
        segment: str = "CASH",
    ) -> Any:
        order_type = "LIMIT" if price and float(price) > 0 else "MARKET"
        payload = {
            "order_id": order_id,
            "quantity": int(quantity),
            "price": float(price) if order_type == "LIMIT" else 0.0,
            "order_type": order_type,
            "validity": "DAY",
            "trigger_price": 0.0,
            "disclosed_quantity": 0,
        }
        response = self._request("PUT", "/v2/order/modify", json_body=payload)
        return self._extract_payload_data(response)

    def cancel_order(self, order_id: str, segment: str = "CASH") -> Any:
        response = self._request("DELETE", "/v2/order/cancel", params={"order_id": order_id})
        return self._extract_payload_data(response)

    def get_order_list(
        self,
        segment: str = "CASH",
        page: int = 0,
        page_size: int = 10,
    ) -> Any:
        response = self._request("GET", "/v2/order/retrieve-all")
        data = self._extract_payload_data(response)
        rows = data if isinstance(data, list) else (data.get("orders", []) if isinstance(data, dict) else [])
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
        response = self._request("GET", "/v2/order/details", params={"order_id": order_id})
        data = self._extract_payload_data(response)
        if isinstance(data, dict):
            details = dict(data)
            details.setdefault("order_id", order_id)
            if "order_status" not in details and "status" in details:
                details["order_status"] = details.get("status")
            return details
        return data

    def get_trades_details(
        self,
        order_id: str,
        segment: str = "CASH",
        page: int = 0,
        page_size: int = 10,
    ) -> Any:
        try:
            response = self._request("GET", "/v2/order/trades/get", params={"order_id": order_id})
        except CustomException:
            response = self._request("GET", "/v2/order/trades", params={"order_id": order_id})
        data = self._extract_payload_data(response)
        rows = data if isinstance(data, list) else (data.get("trades", []) if isinstance(data, dict) else [])
        start = max(0, int(page)) * max(1, int(page_size))
        end = start + max(1, int(page_size))
        return rows[start:end]

    def get_portfolio(self) -> Any:
        response = self._request("GET", "/v2/portfolio/long-term-holdings")
        return self._extract_payload_data(response)

    def get_positions(self, segment: str | None = None) -> Any:
        response = self._request("GET", "/v2/portfolio/short-term-positions")
        data = self._extract_payload_data(response)
        if not segment:
            return data
        if not isinstance(data, list):
            return data
        segment_upper = str(segment).upper()
        filtered = []
        for row in data:
            if not isinstance(row, dict):
                continue
            product = str(row.get("product", "")).upper()
            if segment_upper in {"FUTURES", "FNO"} and product in {"I", "NRML"}:
                filtered.append(row)
            elif segment_upper == "CASH" and product in {"D", "CNC"}:
                filtered.append(row)
        return filtered

    def get_quote(
        self,
        trading_symbol: str,
        exchange: str = "NSE",
        segment: str = "CASH",
    ) -> Any:
        instrument_key = self._resolve_instrument_key(trading_symbol, exchange=exchange, segment=segment)
        response = self._request("GET", "/v2/market-quote/quotes", params={"instrument_key": instrument_key})
        data = self._extract_payload_data(response)
        row = self._extract_quote_row(data, instrument_key)
        ltp = self._extract_ltp(row)
        ohlc = row.get("ohlc", {}) if isinstance(row.get("ohlc"), dict) else {}
        return {
            "source": "upstox",
            "symbol": self._normalize_symbol(trading_symbol),
            "exchange": str(exchange or "NSE").upper(),
            "segment": str(segment or "CASH").upper(),
            "instrument_key": instrument_key,
            "ltp": round(ltp, 4),
            "open": round(self._to_float(ohlc.get("open"), ltp), 4),
            "high": round(self._to_float(ohlc.get("high"), ltp), 4),
            "low": round(self._to_float(ohlc.get("low"), ltp), 4),
            "volume": self._to_int(row.get("volume"), 0),
            "change": round(self._to_float(row.get("net_change"), 0.0), 4),
            "change_pct": round(self._to_float(row.get("percent_change"), 0.0), 4),
            "timestamp": datetime.utcnow().isoformat(),
        }

    def get_ltp(
        self,
        trading_symbol: str,
        exchange: str = "NSE",
        segment: str = "CASH",
    ) -> Any:
        instrument_key = self._resolve_instrument_key(trading_symbol, exchange=exchange, segment=segment)
        response = self._request("GET", "/v2/market-quote/ltp", params={"instrument_key": instrument_key})
        data = self._extract_payload_data(response)
        row = self._extract_quote_row(data, instrument_key)
        ltp = self._extract_ltp(row)
        return {
            "source": "upstox",
            "symbol": self._normalize_symbol(trading_symbol),
            "exchange": str(exchange or "NSE").upper(),
            "segment": str(segment or "CASH").upper(),
            "instrument_key": instrument_key,
            "ltp": round(ltp, 4),
            "timestamp": datetime.utcnow().isoformat(),
        }

    def search_instrument(self, symbol: str, exchange: str | None = None) -> Any:
        query = self._normalize_symbol(symbol)
        if not query:
            return []
        exchange_upper = str(exchange or "").strip().upper()
        rows: list[dict[str, Any]] = []
        for instrument in self._load_instruments():
            instrument_key = str(instrument.get("instrument_key", "")).upper()
            row_symbol = self._get_row_symbol(instrument)
            if exchange_upper and not instrument_key.startswith(f"{exchange_upper}_"):
                continue
            if query not in row_symbol:
                continue
            rows.append(
                {
                    "symbol": row_symbol,
                    "exchange": instrument_key.split("_", 1)[0] if "_" in instrument_key else exchange_upper or "NSE",
                    "segment": instrument_key.split("|", 1)[0] if "|" in instrument_key else "",
                    "instrument_key": instrument_key,
                    "name": instrument.get("name", ""),
                    "lot_size": instrument.get("lot_size"),
                    "tick_size": instrument.get("tick_size"),
                }
            )
            if len(rows) >= 25:
                break
        return rows
