from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import yfinance as yf

from trade_engine.config.market_universe import DEFAULT_SCAN_UNIVERSE


class RecommendationEngine:
    """Generates buy/sell recommendations by scanning a stock universe."""

    def __init__(self, max_workers: int = 8):
        self.max_workers = max_workers

    @staticmethod
    def _fetch_history(symbol: str, period: str, interval: str):
        df = yf.download(
            symbol,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=False,
            threads=False,
        )
        if df is None or df.empty:
            return None
        if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
            df.columns = [c[0] for c in df.columns]
        return df

    @staticmethod
    def _last_signal_row(df, lookback_bars: int):
        signals = df[df["signal"] != 0]
        if signals.empty:
            return None
        idx = signals.index[-1]
        bar_pos = df.index.get_loc(idx)
        if (len(df) - 1 - bar_pos) > max(lookback_bars, 1):
            return None
        return idx, signals.iloc[-1]

    def _score_candidate(self, df, idx, signal_value: int, symbol: str) -> dict[str, Any]:
        close = float(df.loc[idx, "Close"])
        idx_pos = df.index.get_loc(idx)
        recent_return = 0.0
        if idx_pos >= 5:
            prev_close = float(df["Close"].iloc[idx_pos - 5])
            if prev_close > 0:
                recent_return = (close - prev_close) / prev_close

        vol_ratio = 1.0
        vol_sma = float(df["Volume"].rolling(20).mean().iloc[idx_pos]) if idx_pos >= 19 else 0.0
        if vol_sma > 0:
            vol_ratio = float(df["Volume"].iloc[idx_pos]) / vol_sma

        freshness = 1 - ((len(df) - 1 - idx_pos) / max(len(df), 1))
        score = abs(recent_return) * 100 + max(vol_ratio - 1, 0) * 10 + freshness * 5

        return {
            "symbol": symbol,
            "signal": "BUY" if signal_value == 1 else "SELL",
            "signal_date": str(idx),
            "close": round(close, 2),
            "return_5bars_pct": round(recent_return * 100, 2),
            "volume_ratio": round(vol_ratio, 2),
            "score": round(score, 2),
        }

    def _analyze_symbol(
        self,
        symbol: str,
        strategy,
        period: str,
        interval: str,
        lookback_bars: int,
    ) -> dict[str, Any] | None:
        try:
            df = self._fetch_history(symbol, period=period, interval=interval)
            if df is None or len(df) < 50:
                return None

            if hasattr(strategy, "combine_signals"):
                analyzed = strategy.combine_signals(df)
            else:
                analyzed = strategy.calculate_signals(df)

            if "signal" not in analyzed.columns:
                return None

            last_signal = self._last_signal_row(analyzed, lookback_bars=lookback_bars)
            if not last_signal:
                return None

            idx, row = last_signal
            signal_value = int(row["signal"])
            if signal_value not in (1, -1):
                return None

            return self._score_candidate(analyzed, idx, signal_value, symbol)
        except Exception:
            return None

    def recommend(
        self,
        strategy,
        universe: list[str] | None = None,
        top_n: int = 25,
        period: str = "6mo",
        interval: str = "1d",
        lookback_bars: int = 5,
    ) -> dict[str, list[dict[str, Any]]]:
        universe = universe or DEFAULT_SCAN_UNIVERSE
        buy_candidates: list[dict[str, Any]] = []
        sell_candidates: list[dict[str, Any]] = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [
                executor.submit(
                    self._analyze_symbol,
                    symbol,
                    strategy,
                    period,
                    interval,
                    lookback_bars,
                )
                for symbol in universe
            ]

            for future in as_completed(futures):
                result = future.result()
                if not result:
                    continue
                if result["signal"] == "BUY":
                    buy_candidates.append(result)
                else:
                    sell_candidates.append(result)

        buy_candidates.sort(key=lambda x: x["score"], reverse=True)
        sell_candidates.sort(key=lambda x: x["score"], reverse=True)

        return {
            "buy": buy_candidates[:top_n],
            "sell": sell_candidates[:top_n],
            "universe_size": len(universe),
        }



