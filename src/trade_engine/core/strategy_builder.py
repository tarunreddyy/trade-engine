import ast
import os

from trade_engine.config.llm_config import get_llm_provider
from trade_engine.core.llm_factory import LLMFactory

STRATEGY_TEMPLATE = """
from trade_engine.strategies.base_strategy import BaseStrategy
import pandas as pd
import ta


class GeneratedStrategy(BaseStrategy):
    \"\"\"AI-generated trading strategy.\"\"\"

    def __init__(self):
        pass

    def get_description(self) -> str:
        return \"AI-generated strategy: <DESCRIPTION>\"

    def calculate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df[\"signal\"] = 0
        # Strategy logic here
        return df
"""

SYSTEM_PROMPT = f"""You are a Python trading strategy code generator.
You must generate valid Python code that extends BaseStrategy.

Rules:
1. The class MUST be named GeneratedStrategy
2. It MUST extend BaseStrategy from trade_engine.strategies.base_strategy
3. It MUST implement calculate_signals(self, df) returning df with a 'signal' column (1=BUY, -1=SELL, 0=HOLD)
4. It MUST implement get_description(self) returning a string
5. You may use 'ta' (technical analysis) and 'pandas' libraries
6. The df input will have columns: Open, High, Low, Close, Volume
7. Output ONLY the Python code, no markdown fences or explanations

Here is the template to follow:
{STRATEGY_TEMPLATE}
"""


class AIStrategyBuilder:
    """Use an LLM to generate trading strategy code from plain English."""

    def __init__(self, provider=None):
        self.provider = provider or get_llm_provider()
        self.client = LLMFactory.create_llm_client(self.provider)

    def generate_strategy_code(self, description: str) -> str:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Generate a trading strategy that: {description}"},
        ]
        raw = self.client.generate_completion(messages, temperature=0.3)
        return self._clean_code_output(raw)

    def save_strategy(self, code: str, filename: str) -> str:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        gen_dir = os.path.join(base_dir, "strategies", "generated")
        os.makedirs(gen_dir, exist_ok=True)

        if not filename.endswith(".py"):
            filename += ".py"
        filepath = os.path.join(gen_dir, filename)
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(code)
        return filepath

    def _clean_code_output(self, code: str) -> str:
        cleaned = code.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)

        try:
            ast.parse(cleaned)
        except SyntaxError as error:
            raise ValueError(f"Generated code has syntax errors: {error}") from error

        return cleaned
