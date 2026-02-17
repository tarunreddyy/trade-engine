from trade_engine.config.settings_store import get_setting, set_setting

# Available periods for yfinance
VALID_PERIODS = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "ytd", "max"]

# Available intervals for yfinance
VALID_INTERVALS = ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"]

# Chart types
CHART_TYPES = ["candlestick", "line"]

# Available technical indicators
AVAILABLE_INDICATORS = {
    "SMA": "Simple Moving Average",
    "EMA": "Exponential Moving Average",
    "Bollinger": "Bollinger Bands",
    "RSI": "Relative Strength Index",
    "MACD": "MACD (Moving Average Convergence Divergence)",
    "VWAP": "Volume Weighted Average Price",
}


def get_default_period() -> str:
    period = str(get_setting("visualization.default_period", "1mo", str) or "1mo").strip()
    return period if period in VALID_PERIODS else "1mo"


def set_default_period(period: str) -> bool:
    value = str(period or "").strip()
    if value not in VALID_PERIODS:
        raise ValueError(f"Invalid period '{period}'. Valid values: {', '.join(VALID_PERIODS)}")
    return set_setting("visualization.default_period", value)


def get_default_interval() -> str:
    interval = str(get_setting("visualization.default_interval", "1d", str) or "1d").strip()
    return interval if interval in VALID_INTERVALS else "1d"


def set_default_interval(interval: str) -> bool:
    value = str(interval or "").strip()
    if value not in VALID_INTERVALS:
        raise ValueError(f"Invalid interval '{interval}'. Valid values: {', '.join(VALID_INTERVALS)}")
    return set_setting("visualization.default_interval", value)


def get_default_chart_type() -> str:
    chart_type = str(get_setting("visualization.default_chart_type", "candlestick", str) or "candlestick").strip()
    return chart_type if chart_type in CHART_TYPES else "candlestick"


def set_default_chart_type(chart_type: str) -> bool:
    value = str(chart_type or "").strip().lower()
    if value not in CHART_TYPES:
        raise ValueError(f"Invalid chart type '{chart_type}'. Valid values: {', '.join(CHART_TYPES)}")
    return set_setting("visualization.default_chart_type", value)


# Backward-compatible constants.
DEFAULT_PERIOD = get_default_period()
DEFAULT_INTERVAL = get_default_interval()
DEFAULT_CHART_TYPE = get_default_chart_type()
