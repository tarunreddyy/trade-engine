from trade_engine.strategies.sma_crossover import SMACrossoverStrategy
from trade_engine.strategies.rsi_strategy import RSIStrategy
from trade_engine.strategies.macd_strategy import MACDStrategy
from trade_engine.strategies.bollinger_strategy import BollingerStrategy
from trade_engine.strategies.vwap_strategy import VWAPStrategy
from trade_engine.strategies.supertrend_strategy import SupertrendStrategy
from trade_engine.strategies.hlc3_pivot_strategy import HLC3PivotBreakoutStrategy
from trade_engine.strategies.ema_crossover_strategy import EMACrossoverStrategy
from trade_engine.strategies.adx_trend_strategy import ADXTrendStrategy
from trade_engine.strategies.stoch_rsi_strategy import StochRSIStrategy
from trade_engine.strategies.donchian_breakout_strategy import DonchianBreakoutStrategy
from trade_engine.strategies.metadata import STRATEGY_METADATA

STRATEGY_REGISTRY = {
    "SMA Crossover": SMACrossoverStrategy,
    "EMA Crossover": EMACrossoverStrategy,
    "RSI": RSIStrategy,
    "Stoch RSI": StochRSIStrategy,
    "MACD": MACDStrategy,
    "ADX Trend": ADXTrendStrategy,
    "Bollinger Bands": BollingerStrategy,
    "Donchian Breakout": DonchianBreakoutStrategy,
    "VWAP": VWAPStrategy,
    "Supertrend": SupertrendStrategy,
    "HLC3 Pivot Breakout": HLC3PivotBreakoutStrategy,
}

STRATEGY_DETAILS = STRATEGY_METADATA


