import pandas as pd
import ta
from trade_engine.strategies.base_strategy import BaseStrategy


class BollingerStrategy(BaseStrategy):
    """Bollinger Bands strategy: buy on lower band breakout, sell on upper."""

    def __init__(self, period=20, std_dev=2):
        self.period = period
        self.std_dev = std_dev

    def get_description(self) -> str:
        return (
            f"Bollinger Bands (period={self.period}, std_dev={self.std_dev}): "
            "Buy when price crosses below lower band (oversold), "
            "sell when price crosses above upper band (overbought)."
        )

    def calculate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        bb = ta.volatility.BollingerBands(df["Close"], window=self.period, window_dev=self.std_dev)
        df["BB_Upper"] = bb.bollinger_hband()
        df["BB_Lower"] = bb.bollinger_lband()
        df["signal"] = 0

        for i in range(1, len(df)):
            if pd.isna(df["BB_Upper"].iloc[i]) or pd.isna(df["BB_Lower"].iloc[i]):
                continue
            if df["Close"].iloc[i] < df["BB_Lower"].iloc[i] and df["Close"].iloc[i - 1] >= df["BB_Lower"].iloc[i - 1]:
                df.iloc[i, df.columns.get_loc("signal")] = 1
            elif df["Close"].iloc[i] > df["BB_Upper"].iloc[i] and df["Close"].iloc[i - 1] <= df["BB_Upper"].iloc[i - 1]:
                df.iloc[i, df.columns.get_loc("signal")] = -1

        return df


