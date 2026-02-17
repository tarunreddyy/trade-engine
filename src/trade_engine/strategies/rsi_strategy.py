import pandas as pd
import ta
from trade_engine.strategies.base_strategy import BaseStrategy


class RSIStrategy(BaseStrategy):
    """RSI-based strategy: buy when oversold, sell when overbought."""

    def __init__(self, period=14, overbought=70, oversold=30):
        self.period = period
        self.overbought = overbought
        self.oversold = oversold

    def get_description(self) -> str:
        return (
            f"RSI Strategy (period={self.period}, overbought={self.overbought}, "
            f"oversold={self.oversold}): Buy when RSI drops below {self.oversold}, "
            f"sell when RSI rises above {self.overbought}."
        )

    def calculate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["RSI"] = ta.momentum.rsi(df["Close"], window=self.period)
        df["signal"] = 0

        for i in range(1, len(df)):
            if pd.isna(df["RSI"].iloc[i]):
                continue
            if df["RSI"].iloc[i] < self.oversold and df["RSI"].iloc[i - 1] >= self.oversold:
                df.iloc[i, df.columns.get_loc("signal")] = 1
            elif df["RSI"].iloc[i] > self.overbought and df["RSI"].iloc[i - 1] <= self.overbought:
                df.iloc[i, df.columns.get_loc("signal")] = -1

        return df


