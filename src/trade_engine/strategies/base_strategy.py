from abc import ABC, abstractmethod
import pandas as pd


class BaseStrategy(ABC):
    """Abstract base class for all trading strategies.

    Subclasses must implement ``calculate_signals`` which adds a ``signal``
    column to a DataFrame (1 = BUY, -1 = SELL, 0 = HOLD).
    """

    @abstractmethod
    def calculate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate trading signals on OHLCV data.

        Args:
            df: DataFrame with at least Open, High, Low, Close, Volume columns.

        Returns:
            Same DataFrame with an added ``signal`` column.
        """

    @abstractmethod
    def get_description(self) -> str:
        """Return a human-readable description of the strategy."""

    def validate_data(self, df: pd.DataFrame) -> bool:
        """Validate that required columns exist."""
        required = {"Open", "High", "Low", "Close", "Volume"}
        return required.issubset(set(df.columns)) and len(df) > 0


