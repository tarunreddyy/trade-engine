import pandas as pd
import ta
from trade_engine.strategies.base_strategy import BaseStrategy


class MACDStrategy(BaseStrategy):
    """MACD strategy: buy/sell on MACD-signal line crossover."""

    def __init__(self, fast=12, slow=26, signal=9):
        self.fast = fast
        self.slow = slow
        self.signal_period = signal

    def get_description(self) -> str:
        return (
            f"MACD Strategy (fast={self.fast}, slow={self.slow}, signal={self.signal_period}): "
            "Buy when MACD crosses above signal line, sell when it crosses below."
        )

    def calculate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        macd = ta.trend.MACD(df["Close"], window_fast=self.fast, window_slow=self.slow, window_sign=self.signal_period)
        df["MACD"] = macd.macd()
        df["MACD_Signal"] = macd.macd_signal()
        df["signal"] = 0

        for i in range(1, len(df)):
            if pd.isna(df["MACD"].iloc[i]) or pd.isna(df["MACD_Signal"].iloc[i]):
                continue
            if (
                df["MACD"].iloc[i] > df["MACD_Signal"].iloc[i]
                and df["MACD"].iloc[i - 1] <= df["MACD_Signal"].iloc[i - 1]
            ):
                df.iloc[i, df.columns.get_loc("signal")] = 1
            elif (
                df["MACD"].iloc[i] < df["MACD_Signal"].iloc[i]
                and df["MACD"].iloc[i - 1] >= df["MACD_Signal"].iloc[i - 1]
            ):
                df.iloc[i, df.columns.get_loc("signal")] = -1

        return df


