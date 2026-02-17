import pandas as pd
import ta
from trade_engine.strategies.base_strategy import BaseStrategy


class SupertrendStrategy(BaseStrategy):
    """Supertrend (ATR-based) trend-following strategy."""

    def __init__(self, period=10, multiplier=3.0):
        self.period = period
        self.multiplier = multiplier

    def get_description(self) -> str:
        return (
            f"Supertrend (period={self.period}, multiplier={self.multiplier}): "
            "ATR-based trend following. Buy when price crosses above supertrend, "
            "sell when price crosses below."
        )

    def calculate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        atr = ta.volatility.AverageTrueRange(df["High"], df["Low"], df["Close"], window=self.period)
        df["ATR"] = atr.average_true_range()

        hl2 = (df["High"] + df["Low"]) / 2
        df["upper_band"] = hl2 + self.multiplier * df["ATR"]
        df["lower_band"] = hl2 - self.multiplier * df["ATR"]
        df["supertrend"] = 0.0
        df["st_direction"] = 1  # 1 = uptrend, -1 = downtrend

        for i in range(1, len(df)):
            if pd.isna(df["ATR"].iloc[i]):
                continue

            # Adjust bands
            if df["lower_band"].iloc[i] > df["lower_band"].iloc[i - 1] or df["Close"].iloc[i - 1] < df["lower_band"].iloc[i - 1]:
                pass  # keep current lower_band
            else:
                df.iloc[i, df.columns.get_loc("lower_band")] = df["lower_band"].iloc[i - 1]

            if df["upper_band"].iloc[i] < df["upper_band"].iloc[i - 1] or df["Close"].iloc[i - 1] > df["upper_band"].iloc[i - 1]:
                pass
            else:
                df.iloc[i, df.columns.get_loc("upper_band")] = df["upper_band"].iloc[i - 1]

            # Direction
            if df["st_direction"].iloc[i - 1] == 1:
                if df["Close"].iloc[i] < df["lower_band"].iloc[i]:
                    df.iloc[i, df.columns.get_loc("st_direction")] = -1
                    df.iloc[i, df.columns.get_loc("supertrend")] = df["upper_band"].iloc[i]
                else:
                    df.iloc[i, df.columns.get_loc("st_direction")] = 1
                    df.iloc[i, df.columns.get_loc("supertrend")] = df["lower_band"].iloc[i]
            else:
                if df["Close"].iloc[i] > df["upper_band"].iloc[i]:
                    df.iloc[i, df.columns.get_loc("st_direction")] = 1
                    df.iloc[i, df.columns.get_loc("supertrend")] = df["lower_band"].iloc[i]
                else:
                    df.iloc[i, df.columns.get_loc("st_direction")] = -1
                    df.iloc[i, df.columns.get_loc("supertrend")] = df["upper_band"].iloc[i]

        # Generate signals on direction change
        df["signal"] = 0
        for i in range(1, len(df)):
            if df["st_direction"].iloc[i] == 1 and df["st_direction"].iloc[i - 1] == -1:
                df.iloc[i, df.columns.get_loc("signal")] = 1
            elif df["st_direction"].iloc[i] == -1 and df["st_direction"].iloc[i - 1] == 1:
                df.iloc[i, df.columns.get_loc("signal")] = -1

        return df


