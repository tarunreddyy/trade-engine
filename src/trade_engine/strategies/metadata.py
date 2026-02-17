from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class StrategyMetadata:
    name: str
    category: str
    preferred_timeframe: str
    risk_profile: str
    description: str


STRATEGY_METADATA: Dict[str, StrategyMetadata] = {
    "SMA Crossover": StrategyMetadata(
        name="SMA Crossover",
        category="Trend Following",
        preferred_timeframe="1d",
        risk_profile="medium",
        description="Classic moving-average trend filter with moderate trade frequency.",
    ),
    "EMA Crossover": StrategyMetadata(
        name="EMA Crossover",
        category="Trend Following",
        preferred_timeframe="1d",
        risk_profile="medium",
        description="Faster trend-following crossover, more responsive than SMA.",
    ),
    "RSI": StrategyMetadata(
        name="RSI",
        category="Mean Reversion",
        preferred_timeframe="1d",
        risk_profile="low-medium",
        description="Momentum oscillator for oversold/overbought reversals.",
    ),
    "Stoch RSI": StrategyMetadata(
        name="Stoch RSI",
        category="Mean Reversion",
        preferred_timeframe="1d",
        risk_profile="medium",
        description="Faster oscillator variant with higher signal frequency.",
    ),
    "MACD": StrategyMetadata(
        name="MACD",
        category="Momentum",
        preferred_timeframe="1d",
        risk_profile="medium",
        description="Momentum/trend hybrid using EMA spread and signal line.",
    ),
    "ADX Trend": StrategyMetadata(
        name="ADX Trend",
        category="Trend Strength",
        preferred_timeframe="1d",
        risk_profile="medium-high",
        description="Trades trends only when directional strength is significant.",
    ),
    "Bollinger Bands": StrategyMetadata(
        name="Bollinger Bands",
        category="Volatility/Mean Reversion",
        preferred_timeframe="1d",
        risk_profile="medium",
        description="Volatility envelope strategy around moving average bands.",
    ),
    "Donchian Breakout": StrategyMetadata(
        name="Donchian Breakout",
        category="Breakout",
        preferred_timeframe="1d",
        risk_profile="high",
        description="Breakout strategy on rolling highs/lows.",
    ),
    "VWAP": StrategyMetadata(
        name="VWAP",
        category="Intraday Mean Reversion",
        preferred_timeframe="5m",
        risk_profile="medium",
        description="Price-location strategy relative to volume-weighted benchmark.",
    ),
    "Supertrend": StrategyMetadata(
        name="Supertrend",
        category="Trend Following",
        preferred_timeframe="1d",
        risk_profile="medium-high",
        description="ATR-based directional regime filter with trailing behavior.",
    ),
    "HLC3 Pivot Breakout": StrategyMetadata(
        name="HLC3 Pivot Breakout",
        category="Breakout",
        preferred_timeframe="1d",
        risk_profile="high",
        description="Pivot-level breakout logic based on HLC3 price structure.",
    ),
}
