from __future__ import annotations

from typing import Any

from trade_engine.brokers.base_broker import BaseBroker
from trade_engine.core.market_data_service import MarketDataService


class DataOnlyBroker(BaseBroker):
    """Broker-free adapter that provides market data only."""

    def __init__(self):
        self.market_data = MarketDataService()

    @staticmethod
    def _not_available(method_name: str):
        raise NotImplementedError(
            f"DataOnlyBroker.{method_name} is unavailable in broker-free mode. "
            "Choose a broker in Quick Setup to enable order and portfolio actions."
        )

    def authenticate(self) -> str:
        return "data-only"

    def place_order(
        self,
        trading_symbol: str,
        quantity: int,
        price: float,
        exchange: str = "NSE",
        segment: str = "CASH",
        transaction_type: str = "BUY",
    ) -> Any:
        self._not_available("place_order")

    def modify_order(self, order_id: str, quantity: int, price: float, segment: str = "CASH") -> Any:
        self._not_available("modify_order")

    def cancel_order(self, order_id: str, segment: str = "CASH") -> Any:
        self._not_available("cancel_order")

    def get_order_list(self, segment: str = "CASH", page: int = 0, page_size: int = 10) -> Any:
        self._not_available("get_order_list")

    def get_order_status(self, order_id: str, segment: str = "CASH") -> Any:
        self._not_available("get_order_status")

    def get_order_details(self, order_id: str, segment: str = "CASH") -> Any:
        self._not_available("get_order_details")

    def get_trades_details(
        self,
        order_id: str,
        segment: str = "CASH",
        page: int = 0,
        page_size: int = 10,
    ) -> Any:
        self._not_available("get_trades_details")

    def get_portfolio(self) -> Any:
        self._not_available("get_portfolio")

    def get_positions(self, segment: str | None = None) -> Any:
        self._not_available("get_positions")

    def get_quote(self, trading_symbol: str, exchange: str = "NSE", segment: str = "CASH") -> Any:
        return self.market_data.get_quote(trading_symbol=trading_symbol, exchange=exchange, segment=segment)

    def get_ltp(self, trading_symbol: str, exchange: str = "NSE", segment: str = "CASH") -> Any:
        return self.market_data.get_ltp(trading_symbol=trading_symbol, exchange=exchange, segment=segment)

    def search_instrument(self, symbol: str, exchange: str | None = None) -> Any:
        return self.market_data.search_instrument(symbol=symbol, exchange=exchange)
