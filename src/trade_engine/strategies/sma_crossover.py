import pandas as pd
import ta

from trade_engine.strategies.base_strategy import BaseStrategy


class SMACrossoverStrategy(BaseStrategy):
    """SMA crossover strategy: buy when short SMA crosses above long SMA."""

    def __init__(self, short_window=10, long_window=30):
        self.short_window = short_window
        self.long_window = long_window

    def get_description(self) -> str:
        return (
            f"SMA Crossover (short={self.short_window}, long={self.long_window}): "
            "Buy when short-period SMA crosses above long-period SMA, "
            "sell when it crosses below."
        )

    def calculate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["SMA_Short"] = ta.trend.sma_indicator(df["Close"], window=self.short_window)
        df["SMA_Long"] = ta.trend.sma_indicator(df["Close"], window=self.long_window)
        df["signal"] = 0

        for i in range(1, len(df)):
            if pd.isna(df["SMA_Short"].iloc[i]) or pd.isna(df["SMA_Long"].iloc[i]):
                continue
            if (
                df["SMA_Short"].iloc[i] > df["SMA_Long"].iloc[i]
                and df["SMA_Short"].iloc[i - 1] <= df["SMA_Long"].iloc[i - 1]
            ):
                df.iloc[i, df.columns.get_loc("signal")] = 1
            elif (
                df["SMA_Short"].iloc[i] < df["SMA_Long"].iloc[i]
                and df["SMA_Short"].iloc[i - 1] >= df["SMA_Long"].iloc[i - 1]
            ):
                df.iloc[i, df.columns.get_loc("signal")] = -1

        return df




