from abc import ABC, abstractmethod
from typing import Any


class BaseBroker(ABC):
    """Abstract interface for all broker adapters."""

    @abstractmethod
    def authenticate(self) -> str:
        """Authenticate with the broker and return an auth token/session identifier."""

    @abstractmethod
    def place_order(
        self,
        trading_symbol: str,
        quantity: int,
        price: float,
        exchange: str = "NSE",
        segment: str = "CASH",
        transaction_type: str = "BUY",
    ) -> Any:
        """Place a new order."""

    @abstractmethod
    def modify_order(
        self,
        order_id: str,
        quantity: int,
        price: float,
        segment: str = "CASH",
    ) -> Any:
        """Modify an existing order."""

    @abstractmethod
    def cancel_order(self, order_id: str, segment: str = "CASH") -> Any:
        """Cancel an existing order."""

    @abstractmethod
    def get_order_list(
        self,
        segment: str = "CASH",
        page: int = 0,
        page_size: int = 10,
    ) -> Any:
        """Fetch the order list."""

    @abstractmethod
    def get_order_status(self, order_id: str, segment: str = "CASH") -> Any:
        """Fetch order status."""

    @abstractmethod
    def get_order_details(self, order_id: str, segment: str = "CASH") -> Any:
        """Fetch order details."""

    @abstractmethod
    def get_trades_details(
        self,
        order_id: str,
        segment: str = "CASH",
        page: int = 0,
        page_size: int = 10,
    ) -> Any:
        """Fetch trades details for an order."""

    @abstractmethod
    def get_portfolio(self) -> Any:
        """Fetch portfolio holdings."""

    @abstractmethod
    def get_positions(self, segment: str | None = None) -> Any:
        """Fetch positions, optionally by segment."""

    @abstractmethod
    def get_quote(
        self,
        trading_symbol: str,
        exchange: str = "NSE",
        segment: str = "CASH",
    ) -> Any:
        """Fetch live quote."""

    @abstractmethod
    def get_ltp(
        self,
        trading_symbol: str,
        exchange: str = "NSE",
        segment: str = "CASH",
    ) -> Any:
        """Fetch LTP (Last Traded Price)."""

    @abstractmethod
    def search_instrument(self, symbol: str, exchange: str | None = None) -> Any:
        """Search instrument metadata."""


