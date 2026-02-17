import os
from dotenv import load_dotenv

load_dotenv()

# Default visualization settings
DEFAULT_PERIOD = "1mo"
DEFAULT_INTERVAL = "1d"
DEFAULT_CHART_TYPE = "candlestick"

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


