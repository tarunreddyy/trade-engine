import numpy as np
import pandas as pd

from trade_engine.strategies.base_strategy import BaseStrategy


class HLC3PivotBreakoutStrategy(BaseStrategy):
    """Two-Block HLC3 Pivot Breakout (Previous-Day 195-min Sessions).

    Splits the previous trading day into two 195-minute blocks, computes
    the Typical Price (H+L+C)/3 for each block, then uses them as a band:

        upper = max(TP1, TP2)
        lower = min(TP1, TP2)

    Signals:
        BUY  (1)  when Close crosses above the upper band
        SELL (-1) when Close crosses below the lower band
        HOLD (0)  otherwise

    Designed for daily-interval data where the previous day's intraday
    blocks have been pre-computed, or for intraday data where the two
    blocks can be derived directly.
    """

    def __init__(self, block_minutes=195):
        self.block_minutes = block_minutes

    def get_description(self) -> str:
        return (
            f"Two-Block HLC3 Pivot Breakout (block={self.block_minutes}min): "
            "Computes typical price (H+L+C)/3 for two intraday blocks of the "
            "previous session. Uses upper=max(TP1,TP2) and lower=min(TP1,TP2) "
            "as a band. Buy on upper breakout, sell on lower breakdown."
        )

    def calculate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # Determine if we have intraday data (multiple bars per day)
        if hasattr(df.index, 'date'):
            unique_dates = df.index.normalize().unique()
        else:
            unique_dates = pd.Index([])

        is_intraday = len(unique_dates) < len(df) and len(unique_dates) > 0

        if is_intraday:
            df = self._calculate_intraday(df, unique_dates)
        else:
            df = self._calculate_daily(df)

        return df

    def _calculate_daily(self, df: pd.DataFrame) -> pd.DataFrame:
        """For daily data: approximate the two blocks using first/second half
        of the day's range. Each day's HLC3 is one level; we use current and
        previous day's HLC3 as the two pivot levels."""
        df["HLC3"] = (df["High"] + df["Low"] + df["Close"]) / 3

        df["TP1"] = df["HLC3"].shift(1)  # previous day's HLC3
        df["TP2"] = df["HLC3"].shift(2)  # two days ago HLC3

        df["pivot_upper"] = df[["TP1", "TP2"]].max(axis=1)
        df["pivot_lower"] = df[["TP1", "TP2"]].min(axis=1)

        df["signal"] = 0
        for i in range(1, len(df)):
            if pd.isna(df["pivot_upper"].iloc[i]) or pd.isna(df["pivot_lower"].iloc[i]):
                continue

            prev_close = df["Close"].iloc[i - 1]
            curr_close = df["Close"].iloc[i]
            upper = df["pivot_upper"].iloc[i]
            lower = df["pivot_lower"].iloc[i]

            # Band breakout: buy above upper, sell below lower
            if curr_close > upper and prev_close <= upper:
                df.iloc[i, df.columns.get_loc("signal")] = 1
            elif curr_close < lower and prev_close >= lower:
                df.iloc[i, df.columns.get_loc("signal")] = -1

        return df

    def _calculate_intraday(self, df: pd.DataFrame, unique_dates) -> pd.DataFrame:
        """For intraday data: split each day into two blocks of block_minutes,
        compute HLC3 for each block, use previous day's blocks as pivot band."""
        df["signal"] = 0
        df["pivot_upper"] = np.nan
        df["pivot_lower"] = np.nan

        prev_tp1 = None
        prev_tp2 = None

        for date in unique_dates:
            day_mask = df.index.normalize() == date
            day_data = df.loc[day_mask]

            if len(day_data) == 0:
                continue

            # Split into two blocks
            mid = len(day_data) // 2
            block1 = day_data.iloc[:mid] if mid > 0 else day_data
            block2 = day_data.iloc[mid:] if mid > 0 else day_data

            # Compute HLC3 for each block
            tp1 = (block1["High"].max() + block1["Low"].min() + block1["Close"].iloc[-1]) / 3
            tp2 = (block2["High"].max() + block2["Low"].min() + block2["Close"].iloc[-1]) / 3

            # Apply previous day's levels to current day
            if prev_tp1 is not None and prev_tp2 is not None:
                upper = max(prev_tp1, prev_tp2)
                lower = min(prev_tp1, prev_tp2)

                day_indices = df.index[day_mask]
                for idx in day_indices:
                    df.at[idx, "pivot_upper"] = upper
                    df.at[idx, "pivot_lower"] = lower

            # Store for next day
            prev_tp1 = tp1
            prev_tp2 = tp2

        # Generate crossover signals
        for i in range(1, len(df)):
            upper = df["pivot_upper"].iloc[i]
            lower = df["pivot_lower"].iloc[i]
            if pd.isna(upper) or pd.isna(lower):
                continue

            prev_close = df["Close"].iloc[i - 1]
            curr_close = df["Close"].iloc[i]

            if curr_close > upper and prev_close <= upper:
                df.iloc[i, df.columns.get_loc("signal")] = 1
            elif curr_close < lower and prev_close >= lower:
                df.iloc[i, df.columns.get_loc("signal")] = -1

        return df




