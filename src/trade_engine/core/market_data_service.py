from __future__ import annotations

from datetime import datetime
from typing import Any

import yfinance as yf


NSE_INDEX_TICKERS: dict[str, str] = {
    "NIFTY 50": "^NSEI",
    "NIFTY BANK": "^NSEBANK",
    "NIFTY FIN SERVICE": "^CNXFIN",
    "NIFTY IT": "^CNXIT",
}

FNO_DEFAULT_TICKERS: list[str] = [
    "NIFTYBEES.NS",
    "BANKBEES.NS",
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
]


class MarketDataService:
    """Broker-independent market data helper backed by Yahoo Finance."""

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        value = str(symbol or "").strip().upper()
        if not value:
            raise ValueError("Symbol cannot be empty.")
        if value.startswith("^"):
            return value
        if "." not in value and value not in {"NIFTY", "BANKNIFTY"}:
            return f"{value}.NS"
        return value

    @staticmethod
    def _download_ohlc(symbol: str, period: str = "5d", interval: str = "1m"):
        return yf.download(
            symbol,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=False,
            threads=False,
        )

    def get_quote(self, trading_symbol: str, exchange: str = "NSE", segment: str = "CASH") -> dict[str, Any]:
        symbol = self._normalize_symbol(trading_symbol)
        intraday = self._download_ohlc(symbol, period="1d", interval="1m")
        if intraday is None or intraday.empty:
            fallback = self._download_ohlc(symbol, period="5d", interval="1d")
            if fallback is None or fallback.empty:
                raise ValueError(f"No market data found for symbol '{symbol}'")
            intraday = fallback

        if hasattr(intraday.columns, "nlevels") and intraday.columns.nlevels > 1:
            intraday.columns = [c[0] for c in intraday.columns]

        last = intraday.iloc[-1]
        prev_close = float(intraday["Close"].iloc[-2]) if len(intraday) > 1 else float(last["Close"])
        close = float(last["Close"])
        change = close - prev_close
        change_pct = (change / prev_close * 100.0) if prev_close else 0.0
        return {
            "source": "yfinance",
            "symbol": symbol,
            "exchange": exchange.upper(),
            "segment": segment.upper(),
            "ltp": round(close, 4),
            "open": round(float(last.get("Open", close)), 4),
            "high": round(float(last.get("High", close)), 4),
            "low": round(float(last.get("Low", close)), 4),
            "volume": int(last.get("Volume", 0) or 0),
            "change": round(change, 4),
            "change_pct": round(change_pct, 4),
            "timestamp": datetime.utcnow().isoformat(),
        }

    def get_ltp(self, trading_symbol: str, exchange: str = "NSE", segment: str = "CASH") -> dict[str, Any]:
        quote = self.get_quote(trading_symbol=trading_symbol, exchange=exchange, segment=segment)
        return {
            "source": quote["source"],
            "symbol": quote["symbol"],
            "exchange": quote["exchange"],
            "segment": quote["segment"],
            "ltp": quote["ltp"],
            "timestamp": quote["timestamp"],
        }

    def search_instrument(self, symbol: str, exchange: str | None = None) -> list[dict[str, Any]]:
        value = str(symbol or "").strip().upper()
        if not value:
            return []
        candidates: list[str] = []
        if "." in value or value.startswith("^"):
            candidates.append(value)
        else:
            candidates.extend([f"{value}.NS", f"{value}.BO", value])

        results: list[dict[str, Any]] = []
        for candidate in candidates:
            try:
                quote = self.get_ltp(candidate, exchange=exchange or "NSE", segment="CASH")
                results.append(
                    {
                        "symbol": quote["symbol"],
                        "exchange": exchange or "NSE",
                        "segment": "CASH",
                        "ltp": quote["ltp"],
                        "source": "yfinance",
                    }
                )
            except Exception:
                continue
        return results

    def get_batch_snapshot(self, symbols: list[str], exchange: str = "NSE", segment: str = "CASH") -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for symbol in symbols:
            try:
                quote = self.get_quote(symbol, exchange=exchange, segment=segment)
                rows.append(quote)
            except Exception:
                continue
        return rows

    def get_indices_snapshot(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for name, ticker in NSE_INDEX_TICKERS.items():
            try:
                quote = self.get_quote(ticker, exchange="NSE", segment="INDEX")
                rows.append(
                    {
                        "name": name,
                        "symbol": ticker,
                        "ltp": quote["ltp"],
                        "change_pct": quote["change_pct"],
                        "timestamp": quote["timestamp"],
                    }
                )
            except Exception:
                continue
        return rows

    def get_fno_snapshot(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for ticker in FNO_DEFAULT_TICKERS:
            try:
                quote = self.get_quote(ticker, exchange="NSE", segment="FNO")
                rows.append(
                    {
                        "symbol": quote["symbol"],
                        "ltp": quote["ltp"],
                        "change_pct": quote["change_pct"],
                        "timestamp": quote["timestamp"],
                    }
                )
            except Exception:
                continue
        return rows
