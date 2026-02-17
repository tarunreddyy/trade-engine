from datetime import datetime
from typing import Any

import yfinance as yf

from trade_engine.config.market_universe import (
    DEFAULT_FNO_UNIVERSE,
    DEFAULT_SCAN_UNIVERSE,
    NSE_INDEX_UNIVERSE,
)

FNO_DEFAULT_TICKERS: list[str] = list(dict.fromkeys(DEFAULT_FNO_UNIVERSE))

_INDEX_ALIAS_TO_TICKER: dict[str, str] = {}
_INDEX_META_BY_TICKER: dict[str, dict[str, str]] = {}
for _row in NSE_INDEX_UNIVERSE:
    _name = str(_row.get("name", "")).upper()
    _symbol = str(_row.get("symbol", "")).upper()
    _ticker = str(_row.get("ticker", "")).upper()
    if not _ticker:
        continue
    _INDEX_META_BY_TICKER[_ticker] = {
        "name": _name,
        "symbol": _symbol,
        "ticker": _ticker,
    }
    for _alias in {_name, _name.replace(" ", ""), _symbol, _ticker}:
        if _alias:
            _INDEX_ALIAS_TO_TICKER[_alias] = _ticker


class MarketDataService:
    """Broker-independent market data helper backed by Yahoo Finance."""

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        value = str(symbol or "").strip().upper()
        if not value:
            raise ValueError("Symbol cannot be empty.")
        if value in _INDEX_ALIAS_TO_TICKER:
            return _INDEX_ALIAS_TO_TICKER[value]
        if value.startswith("^"):
            return value
        if "." not in value:
            return f"{value}.NS"
        return value

    @staticmethod
    def _segment_for_symbol(symbol: str) -> str:
        if symbol.startswith("^"):
            return "INDEX"
        if symbol in set(FNO_DEFAULT_TICKERS):
            return "FNO"
        return "CASH"

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

    @staticmethod
    def _symbol_key(symbol: str) -> str:
        raw = str(symbol or "").upper()
        if raw.startswith("^"):
            return raw
        return raw.replace(".NS", "").replace(".BO", "")

    def search_instrument(self, symbol: str, exchange: str | None = None) -> list[dict[str, Any]]:
        query = str(symbol or "").strip().upper()
        if not query:
            return []

        fno_set = set(FNO_DEFAULT_TICKERS)
        scan_candidates = list(dict.fromkeys([*DEFAULT_SCAN_UNIVERSE, *FNO_DEFAULT_TICKERS]))
        index_matches: list[str] = []
        for row in NSE_INDEX_UNIVERSE:
            name = str(row.get("name", "")).upper()
            display_symbol = str(row.get("symbol", "")).upper()
            ticker = str(row.get("ticker", "")).upper()
            if query in name or query in display_symbol or query in ticker:
                index_matches.append(ticker)

        eq_fno_matches = [item for item in scan_candidates if query in self._symbol_key(item)]
        direct_match = self._normalize_symbol(query) if query not in {"NIFTY", "BANKNIFTY"} else self._normalize_symbol(query)
        ordered_matches = list(dict.fromkeys([direct_match, *index_matches, *eq_fno_matches]))

        results: list[dict[str, Any]] = []
        for candidate in ordered_matches[:35]:
            segment = "INDEX" if candidate.startswith("^") else ("FNO" if candidate in fno_set else "CASH")
            try:
                quote = self.get_ltp(candidate, exchange=exchange or "NSE", segment=segment)
                index_meta = _INDEX_META_BY_TICKER.get(quote["symbol"], {})
                display_symbol = str(index_meta.get("symbol", quote["symbol"]))
                display_name = str(index_meta.get("name", display_symbol))
                results.append(
                    {
                        "symbol": display_symbol,
                        "name": display_name,
                        "trading_symbol": quote["symbol"],
                        "exchange": exchange or "NSE",
                        "segment": segment,
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
                normalized = self._normalize_symbol(symbol)
                resolved_segment = segment if segment != "AUTO" else self._segment_for_symbol(normalized)
                quote = self.get_quote(normalized, exchange=exchange, segment=resolved_segment)
                rows.append(quote)
            except Exception:
                continue
        return rows

    def get_indices_snapshot(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for row in NSE_INDEX_UNIVERSE:
            name = str(row.get("name", ""))
            display_symbol = str(row.get("symbol", ""))
            ticker = str(row.get("ticker", ""))
            if not ticker:
                continue
            try:
                quote = self.get_quote(ticker, exchange="NSE", segment="INDEX")
                rows.append(
                    {
                        "name": name,
                        "symbol": display_symbol or ticker,
                        "ticker": ticker,
                        "ltp": quote["ltp"],
                        "change_pct": quote["change_pct"],
                        "timestamp": quote["timestamp"],
                    }
                )
            except Exception:
                continue
        return rows

    def get_fno_snapshot(self, limit: int = 30) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for ticker in FNO_DEFAULT_TICKERS:
            if len(rows) >= max(1, int(limit)):
                break
            segment = "INDEX" if ticker.startswith("^") else "FNO"
            try:
                quote = self.get_quote(ticker, exchange="NSE", segment=segment)
                display_symbol = quote["symbol"].replace(".NS", "")
                rows.append(
                    {
                        "symbol": display_symbol,
                        "trading_symbol": quote["symbol"],
                        "segment": segment,
                        "ltp": quote["ltp"],
                        "change_pct": quote["change_pct"],
                        "timestamp": quote["timestamp"],
                    }
                )
            except Exception:
                continue
        return rows
