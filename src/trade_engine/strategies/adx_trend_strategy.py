import pandas as pd
import ta

from trade_engine.strategies.base_strategy import BaseStrategy


class ADXTrendStrategy(BaseStrategy):
    """Trend-following strategy using ADX + DI crossovers."""

    def __init__(self, adx_period=14, adx_threshold=20):
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold

    def get_description(self) -> str:
        return (
            f"ADX Trend (period={self.adx_period}, threshold={self.adx_threshold}): "
            "Buy on +DI/-DI bullish crossover when ADX confirms trend strength; "
            "sell on bearish crossover under same condition."
        )

    def calculate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        adx_ind = ta.trend.ADXIndicator(
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            window=self.adx_period,
        )
        df["ADX"] = adx_ind.adx()
        df["+DI"] = adx_ind.adx_pos()
        df["-DI"] = adx_ind.adx_neg()
        df["signal"] = 0

        for i in range(1, len(df)):
            if pd.isna(df["ADX"].iloc[i]):
                continue
            strong_trend = df["ADX"].iloc[i] >= self.adx_threshold
            bullish_cross = df["+DI"].iloc[i] > df["-DI"].iloc[i] and df["+DI"].iloc[i - 1] <= df["-DI"].iloc[i - 1]
            bearish_cross = df["+DI"].iloc[i] < df["-DI"].iloc[i] and df["+DI"].iloc[i - 1] >= df["-DI"].iloc[i - 1]

            if strong_trend and bullish_cross:
                df.iloc[i, df.columns.get_loc("signal")] = 1
            elif strong_trend and bearish_cross:
                df.iloc[i, df.columns.get_loc("signal")] = -1

        return df


