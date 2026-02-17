from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple

import yfinance as yf

from trade_engine.config.strategy_config import DEFAULT_INITIAL_CAPITAL, STRATEGY_DEFAULTS
from trade_engine.strategies import STRATEGY_REGISTRY
from trade_engine.strategies.backtester import Backtester


class StrategyLeaderboard:
    """Builds a ranked leaderboard across strategies and symbols."""

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
            return symbol, None
        if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
            df.columns = [col[0] for col in df.columns]
        if len(df) < 80:
            return symbol, None
        return symbol, df

    @staticmethod
    def _build_strategy(strategy_name: str):
        cls = STRATEGY_REGISTRY[strategy_name]
        key = strategy_name.replace(" ", "_")
        defaults = STRATEGY_DEFAULTS.get(key, {})
        return cls(**defaults)

    @staticmethod
    def _score_result(result: dict) -> float:
        total_return = float(result.get("total_return", 0.0))
        total_costs = float(result.get("total_costs", 0.0))
        initial_capital = float(result.get("initial_capital", 1.0)) or 1.0
        cost_drag_pct = (total_costs / initial_capital) * 100.0
        sharpe = float(result.get("sharpe_ratio", 0.0))
        drawdown = abs(float(result.get("max_drawdown", 0.0)))
        win_rate = float(result.get("win_rate", 0.0))
        trades = float(result.get("total_trades", 0))

        quality_bonus = min(trades, 40.0) * 0.1
        return round(
            (0.45 * total_return)
            + (12.0 * sharpe)
            + (0.18 * win_rate)
            - (0.35 * drawdown)
            - (0.50 * cost_drag_pct)
            + quality_bonus,
            3,
        )

    def _evaluate_pair(
        self,
        strategy_name: str,
        symbol: str,
        df,
        initial_capital: float,
    ) -> Optional[dict]:
        try:
            strategy = self._build_strategy(strategy_name)
            backtester = Backtester()
            result = backtester.run_backtest(df.copy(), strategy, initial_capital=initial_capital)
            score = self._score_result(result)
            return {
                "strategy": strategy_name,
                "symbol": symbol,
                "score": score,
                "total_return_pct": result.get("total_return", 0.0),
                "sharpe_ratio": result.get("sharpe_ratio", 0.0),
                "max_drawdown_pct": result.get("max_drawdown", 0.0),
                "win_rate_pct": result.get("win_rate", 0.0),
                "trades": result.get("total_trades", 0),
                "final_value": result.get("final_value", 0.0),
                "total_costs": result.get("total_costs", 0.0),
            }
        except Exception:
            return None

    def build(
        self,
        symbols: List[str],
        period: str = "1y",
        interval: str = "1d",
        top_n: int = 25,
        initial_capital: float = DEFAULT_INITIAL_CAPITAL,
    ) -> dict:
        unique_symbols = [symbol.upper() for symbol in symbols if symbol.strip()]
        if not unique_symbols:
            return {
                "rows": [],
                "strategy_summary": [],
                "symbols_scanned": 0,
                "pair_count": 0,
                "message": "No symbols provided.",
            }

        data_cache: Dict[str, Any] = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self._fetch_history, symbol, period, interval) for symbol in unique_symbols]
            for future in as_completed(futures):
                symbol, df = future.result()
                if df is not None:
                    data_cache[symbol] = df

        if not data_cache:
            return {
                "rows": [],
                "strategy_summary": [],
                "symbols_scanned": 0,
                "pair_count": 0,
                "message": "No valid market data found for requested symbols.",
            }

        strategy_names = list(STRATEGY_REGISTRY.keys())
        rows: List[dict] = []

        eval_jobs: List[Tuple[str, str, Any]] = []
        for strategy_name in strategy_names:
            for symbol, df in data_cache.items():
                eval_jobs.append((strategy_name, symbol, df))

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [
                executor.submit(self._evaluate_pair, strategy_name, symbol, df, initial_capital)
                for strategy_name, symbol, df in eval_jobs
            ]
            for future in as_completed(futures):
                row = future.result()
                if row:
                    rows.append(row)

        rows.sort(key=lambda item: item["score"], reverse=True)
        top_rows = rows[:max(1, top_n)]

        strategy_buckets: Dict[str, List[dict]] = {}
        for row in rows:
            strategy_buckets.setdefault(row["strategy"], []).append(row)

        strategy_summary: List[dict] = []
        for strategy_name, bucket in strategy_buckets.items():
            count = len(bucket)
            if count == 0:
                continue
            strategy_summary.append(
                {
                    "strategy": strategy_name,
                    "avg_score": round(sum(item["score"] for item in bucket) / count, 3),
                    "avg_return_pct": round(sum(float(item["total_return_pct"]) for item in bucket) / count, 3),
                    "avg_sharpe": round(sum(float(item["sharpe_ratio"]) for item in bucket) / count, 3),
                    "avg_drawdown_pct": round(sum(float(item["max_drawdown_pct"]) for item in bucket) / count, 3),
                    "avg_win_rate_pct": round(sum(float(item["win_rate_pct"]) for item in bucket) / count, 3),
                    "avg_total_costs": round(sum(float(item["total_costs"]) for item in bucket) / count, 3),
                    "samples": count,
                }
            )

        strategy_summary.sort(key=lambda item: item["avg_score"], reverse=True)

        return {
            "rows": top_rows,
            "strategy_summary": strategy_summary,
            "symbols_scanned": len(data_cache),
            "pair_count": len(rows),
            "message": f"Evaluated {len(rows)} strategy-symbol pairs.",
        }


