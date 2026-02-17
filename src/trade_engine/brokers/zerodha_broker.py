import os
from typing import Any, Optional

from dotenv import load_dotenv

from trade_engine.brokers.base_broker import BaseBroker

load_dotenv()


class ZerodhaBroker(BaseBroker):
    """Zerodha adapter stub."""

    def __init__(self):
        self.api_key = os.getenv("ZERODHA_API_KEY")
        self.api_secret = os.getenv("ZERODHA_API_SECRET")

    @staticmethod
    def _not_implemented(method_name: str):
        raise NotImplementedError(
            f"ZerodhaBroker.{method_name} is not implemented yet. "
            "Set BROKER=groww or implement the Zerodha adapter."
        )

    def authenticate(self) -> str:
        self._not_implemented("authenticate")

    def place_order(
        self,
        trading_symbol: str,
        quantity: int,
        price: float,
        exchange: str = "NSE",
        segment: str = "CASH",
        transaction_type: str = "BUY",
    ) -> Any:
        self._not_implemented("place_order")

    def modify_order(
        self,
        order_id: str,
        quantity: int,
        price: float,
        segment: str = "CASH",
    ) -> Any:
        self._not_implemented("modify_order")

    def cancel_order(self, order_id: str, segment: str = "CASH") -> Any:
        self._not_implemented("cancel_order")

    def get_order_list(
        self,
        segment: str = "CASH",
        page: int = 0,
        page_size: int = 10,
    ) -> Any:
        self._not_implemented("get_order_list")

    def get_order_status(self, order_id: str, segment: str = "CASH") -> Any:
        self._not_implemented("get_order_status")

    def get_order_details(self, order_id: str, segment: str = "CASH") -> Any:
        self._not_implemented("get_order_details")

    def get_trades_details(
        self,
        order_id: str,
        segment: str = "CASH",
        page: int = 0,
        page_size: int = 10,
    ) -> Any:
        self._not_implemented("get_trades_details")

    def get_portfolio(self) -> Any:
        self._not_implemented("get_portfolio")

    def get_positions(self, segment: Optional[str] = None) -> Any:
        self._not_implemented("get_positions")

    def get_quote(
        self,
        trading_symbol: str,
        exchange: str = "NSE",
        segment: str = "CASH",
    ) -> Any:
        self._not_implemented("get_quote")

    def get_ltp(
        self,
        trading_symbol: str,
        exchange: str = "NSE",
        segment: str = "CASH",
    ) -> Any:
        self._not_implemented("get_ltp")

    def search_instrument(self, symbol: str, exchange: Optional[str] = None) -> Any:
        self._not_implemented("search_instrument")


