import pandas as pd
from trade_engine.strategies.base_strategy import BaseStrategy


class StrategyCombiner:
    """Combine signals from multiple strategies."""

    def __init__(self, strategies: list[BaseStrategy], mode="majority"):
        """
        Args:
            strategies: List of BaseStrategy instances.
            mode: 'all' (unanimous), 'any' (at least one), 'majority'.
        """
        self.strategies = strategies
        self.mode = mode

    def combine_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        signal_cols = []

        for idx, strategy in enumerate(self.strategies):
            result = strategy.calculate_signals(df.copy())
            col_name = f"signal_{idx}"
            df[col_name] = result["signal"]
            signal_cols.append(col_name)

        df["signal"] = 0

        for i in range(len(df)):
            signals = [df[col].iloc[i] for col in signal_cols]
            buy_count = signals.count(1)
            sell_count = signals.count(-1)
            total = len(signals)

            if self.mode == "all":
                if buy_count == total:
                    df.iloc[i, df.columns.get_loc("signal")] = 1
                elif sell_count == total:
                    df.iloc[i, df.columns.get_loc("signal")] = -1
            elif self.mode == "any":
                if buy_count > 0:
                    df.iloc[i, df.columns.get_loc("signal")] = 1
                elif sell_count > 0:
                    df.iloc[i, df.columns.get_loc("signal")] = -1
            elif self.mode == "majority":
                if buy_count > total / 2:
                    df.iloc[i, df.columns.get_loc("signal")] = 1
                elif sell_count > total / 2:
                    df.iloc[i, df.columns.get_loc("signal")] = -1

        # Clean up individual signal columns
        df.drop(columns=signal_cols, inplace=True)
        return df


