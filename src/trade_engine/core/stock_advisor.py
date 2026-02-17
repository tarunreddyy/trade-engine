import ta
import yfinance as yf

from trade_engine.config.llm_config import get_llm_provider
from trade_engine.core.llm_factory import LLMFactory


class AIStockAdvisor:
    """AI-powered stock analysis and recommendations."""

    def __init__(self, provider=None):
        self.provider = provider or get_llm_provider()
        self.client = LLMFactory.create_llm_client(self.provider)

    def analyze_stock(self, symbol: str, analysis_type: str = "comprehensive") -> str:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="6mo", interval="1d")
        if df.empty:
            raise ValueError(f"No data found for symbol '{symbol}'")

        metrics = self._calculate_stock_metrics(df)
        info = ticker.info

        prompt_data = (
            f"Stock: {symbol}\n"
            f"Company: {info.get('shortName', 'N/A')}\n"
            f"Sector: {info.get('sector', 'N/A')}\n"
            f"Industry: {info.get('industry', 'N/A')}\n"
            f"Current Price: {metrics['current_price']}\n"
            f"52-Week High: {metrics['high_52w']}\n"
            f"52-Week Low: {metrics['low_52w']}\n"
            f"RSI (14): {metrics['rsi']}\n"
            f"SMA 20: {metrics['sma_20']}\n"
            f"SMA 50: {metrics['sma_50']}\n"
            f"Volatility (30d): {metrics['volatility']}\n"
            f"Avg Volume: {metrics['avg_volume']}\n"
            f"Market Cap: {info.get('marketCap', 'N/A')}\n"
            f"PE Ratio: {info.get('trailingPE', 'N/A')}\n"
        )

        analysis_prompts = {
            "comprehensive": "Provide trend, momentum, support/resistance, and overall recommendation.",
            "technical": "Focus on technical analysis: patterns, indicators, support/resistance.",
            "fundamental": "Focus on fundamental analysis: valuation, growth, financial health.",
            "risk": "Analyze risk profile: volatility, drawdown potential, position sizing advice.",
        }
        instruction = analysis_prompts.get(analysis_type, analysis_prompts["comprehensive"])

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert stock analyst. Provide clear, actionable analysis. "
                    "Always include a disclaimer that this is not financial advice."
                ),
            },
            {"role": "user", "content": f"Analyze this stock:\n\n{prompt_data}\n\n{instruction}"},
        ]
        return self.client.generate_completion(messages, temperature=0.5)

    def recommend_stocks(self, criteria: str, count: int = 5) -> str:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert stock analyst. For recommendations provide ticker, rationale, and key metrics. "
                    "Focus on Indian market (NSE/BSE) stocks unless specified otherwise. "
                    "Always include a disclaimer that this is not financial advice."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Recommend {count} stocks matching this criteria: {criteria}\n"
                    "For each stock provide Symbol, Name, Why it fits, Key metrics."
                ),
            },
        ]
        return self.client.generate_completion(messages, temperature=0.5)

    def _calculate_stock_metrics(self, df):
        close = df["Close"]
        rsi = ta.momentum.rsi(close, window=14)
        sma_20 = ta.trend.sma_indicator(close, window=20)
        sma_50 = ta.trend.sma_indicator(close, window=50)
        volatility = close.pct_change().rolling(window=30).std().iloc[-1] * 100

        return {
            "current_price": round(close.iloc[-1], 2),
            "high_52w": round(close.rolling(window=252, min_periods=1).max().iloc[-1], 2),
            "low_52w": round(close.rolling(window=252, min_periods=1).min().iloc[-1], 2),
            "rsi": round(rsi.iloc[-1], 2) if not rsi.empty else "N/A",
            "sma_20": round(sma_20.iloc[-1], 2) if not sma_20.empty else "N/A",
            "sma_50": round(sma_50.iloc[-1], 2) if not sma_50.empty else "N/A",
            "volatility": round(volatility, 2) if volatility == volatility else "N/A",
            "avg_volume": int(df["Volume"].mean()),
        }
