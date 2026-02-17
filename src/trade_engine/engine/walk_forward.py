from typing import Dict, Optional

import pandas as pd

from trade_engine.strategies.backtester import Backtester


class WalkForwardEvaluator:
    """Evaluates strategies with rolling train/test windows and reports out-of-sample performance."""

    def __init__(self):
        self.backtester = Backtester()

    @staticmethod
    def _window_slices(length: int, windows: int) -> list[tuple[int, int, int, int]]:
        windows = max(1, windows)
        segment = max(20, length // (windows + 1))
        slices = []
        for i in range(windows):
            train_start = i * segment
            train_end = train_start + segment
            test_start = train_end
            test_end = min(length, test_start + segment)
            if test_end - test_start < 10:
                break
            slices.append((train_start, train_end, test_start, test_end))
        return slices

    def evaluate(
        self,
        df: pd.DataFrame,
        strategy,
        initial_capital: float,
        windows: int = 3,
    ) -> Optional[Dict[str, float]]:
        if df is None or df.empty or len(df) < 80:
            return None

        slices = self._window_slices(len(df), windows)
        if not slices:
            return None

        oos_results = []
        for _, _, test_start, test_end in slices:
            test_df = df.iloc[test_start:test_end].copy()
            if test_df.empty or len(test_df) < 20:
                continue
            result = self.backtester.run_backtest(test_df, strategy, initial_capital=initial_capital)
            oos_results.append(result)

        if not oos_results:
            return None

        count = len(oos_results)
        avg_return = sum(float(x.get("total_return", 0.0)) for x in oos_results) / count
        avg_sharpe = sum(float(x.get("sharpe_ratio", 0.0)) for x in oos_results) / count
        avg_drawdown = sum(float(x.get("max_drawdown", 0.0)) for x in oos_results) / count
        avg_win_rate = sum(float(x.get("win_rate", 0.0)) for x in oos_results) / count
        avg_costs = sum(float(x.get("total_costs", 0.0)) for x in oos_results) / count
        avg_trades = sum(float(x.get("total_trades", 0.0)) for x in oos_results) / count
        avg_final_value = sum(float(x.get("final_value", initial_capital)) for x in oos_results) / count

        return {
            "total_return": round(avg_return, 3),
            "sharpe_ratio": round(avg_sharpe, 3),
            "max_drawdown": round(avg_drawdown, 3),
            "win_rate": round(avg_win_rate, 3),
            "total_costs": round(avg_costs, 3),
            "total_trades": round(avg_trades, 3),
            "final_value": round(avg_final_value, 3),
            "initial_capital": initial_capital,
            "oos_windows": count,
        }
