import pandas as pd

from trade_engine.strategies.base_strategy import BaseStrategy


class DonchianBreakoutStrategy(BaseStrategy):
    """Donchian channel breakout strategy."""

    def __init__(self, window=20):
        self.window = window

    def get_description(self) -> str:
        return (
            f"Donchian Breakout (window={self.window}): "
            "Buy on breakout above prior channel high, sell below prior channel low."
        )

    def calculate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["Donchian_High"] = df["High"].rolling(self.window).max().shift(1)
        df["Donchian_Low"] = df["Low"].rolling(self.window).min().shift(1)
        df["signal"] = 0

        for i in range(1, len(df)):
            high_band = df["Donchian_High"].iloc[i]
            low_band = df["Donchian_Low"].iloc[i]
            close = df["Close"].iloc[i]
            prev_close = df["Close"].iloc[i - 1]
            if pd.isna(high_band) or pd.isna(low_band):
                continue
            if close > high_band and prev_close <= high_band:
                df.iloc[i, df.columns.get_loc("signal")] = 1
            elif close < low_band and prev_close >= low_band:
                df.iloc[i, df.columns.get_loc("signal")] = -1

        return df


