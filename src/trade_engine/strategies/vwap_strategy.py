import pandas as pd

from trade_engine.strategies.base_strategy import BaseStrategy


class VWAPStrategy(BaseStrategy):
    """VWAP mean-reversion strategy."""

    def __init__(self, deviation=0.02):
        self.deviation = deviation

    def get_description(self) -> str:
        return (
            f"VWAP Strategy (deviation={self.deviation}): "
            "Buy when price is below VWAP by deviation threshold, "
            "sell when price is above VWAP by deviation threshold."
        )

    def calculate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        cumulative_tp_vol = ((df["High"] + df["Low"] + df["Close"]) / 3 * df["Volume"]).cumsum()
        cumulative_vol = df["Volume"].cumsum()
        df["VWAP"] = cumulative_tp_vol / cumulative_vol
        df["signal"] = 0

        for i in range(1, len(df)):
            if pd.isna(df["VWAP"].iloc[i]) or df["VWAP"].iloc[i] == 0:
                continue
            pct_diff = (df["Close"].iloc[i] - df["VWAP"].iloc[i]) / df["VWAP"].iloc[i]
            prev_pct = (df["Close"].iloc[i - 1] - df["VWAP"].iloc[i - 1]) / df["VWAP"].iloc[i - 1] if df["VWAP"].iloc[i - 1] != 0 else 0
            if pct_diff < -self.deviation and prev_pct >= -self.deviation:
                df.iloc[i, df.columns.get_loc("signal")] = 1
            elif pct_diff > self.deviation and prev_pct <= self.deviation:
                df.iloc[i, df.columns.get_loc("signal")] = -1

        return df




