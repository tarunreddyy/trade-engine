import pandas as pd
import ta

from trade_engine.strategies.base_strategy import BaseStrategy


class StochRSIStrategy(BaseStrategy):
    """Momentum strategy using Stochastic RSI crosses in extreme zones."""

    def __init__(self, rsi_period=14, stoch_period=14, smooth_k=3, smooth_d=3, overbought=0.8, oversold=0.2):
        self.rsi_period = rsi_period
        self.stoch_period = stoch_period
        self.smooth_k = smooth_k
        self.smooth_d = smooth_d
        self.overbought = overbought
        self.oversold = oversold

    def get_description(self) -> str:
        return (
            "Stoch RSI: Buy on K/D bullish cross from oversold zone, "
            "sell on bearish cross from overbought zone."
        )

    def calculate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        stoch_rsi = ta.momentum.StochRSIIndicator(
            close=df["Close"],
            window=self.rsi_period,
            smooth1=self.smooth_k,
            smooth2=self.smooth_d,
        )
        df["StochRSI_K"] = stoch_rsi.stochrsi_k()
        df["StochRSI_D"] = stoch_rsi.stochrsi_d()
        df["signal"] = 0

        for i in range(1, len(df)):
            k = df["StochRSI_K"].iloc[i]
            d = df["StochRSI_D"].iloc[i]
            prev_k = df["StochRSI_K"].iloc[i - 1]
            prev_d = df["StochRSI_D"].iloc[i - 1]
            if pd.isna(k) or pd.isna(d):
                continue

            bullish_cross = k > d and prev_k <= prev_d and k <= self.oversold + 0.2
            bearish_cross = k < d and prev_k >= prev_d and k >= self.overbought - 0.2

            if bullish_cross:
                df.iloc[i, df.columns.get_loc("signal")] = 1
            elif bearish_cross:
                df.iloc[i, df.columns.get_loc("signal")] = -1

        return df


