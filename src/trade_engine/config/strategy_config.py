DEFAULT_INITIAL_CAPITAL = 100000
DEFAULT_COMMISSION = 0.001

# Default strategy parameters
STRATEGY_DEFAULTS = {
    "SMA_Crossover": {"short_window": 10, "long_window": 30},
    "EMA_Crossover": {"short_window": 12, "long_window": 26},
    "RSI": {"period": 14, "overbought": 70, "oversold": 30},
    "Stoch_RSI": {"rsi_period": 14, "stoch_period": 14, "smooth_k": 3, "smooth_d": 3, "overbought": 0.8, "oversold": 0.2},
    "MACD": {"fast": 12, "slow": 26, "signal": 9},
    "ADX_Trend": {"adx_period": 14, "adx_threshold": 20},
    "Bollinger_Bands": {"period": 20, "std_dev": 2},
    "Donchian_Breakout": {"window": 20},
    "VWAP": {"deviation": 0.02},
    "Supertrend": {"period": 10, "multiplier": 3.0},
    "HLC3_Pivot_Breakout": {"block_minutes": 195},
}

COMBINE_MODES = ["all", "any", "majority"]


