import os
import secrets
import string
import sys
from typing import Any

from dotenv import load_dotenv

from trade_engine.brokers.base_broker import BaseBroker
from trade_engine.config.groww_config import (
    get_groww_access_token,
    get_groww_api_key,
    get_groww_api_secret,
    set_groww_access_token,
)
from trade_engine.exception.exception import CustomException
from trade_engine.logging.logger import logging

load_dotenv()


class GrowwBroker(BaseBroker):
    """Groww adapter that implements the broker abstraction."""

    def __init__(
        self,
        groww_api_key: str | None = None,
        groww_api_secret: str | None = None,
        auth_token: str | None = None,
    ):
        self.groww_api_key = groww_api_key or get_groww_api_key()
        self.groww_api_secret = groww_api_secret or get_groww_api_secret()
        self.groww_auth_token = auth_token or get_groww_access_token() or os.getenv("GROWW_ACCESS_TOKEN")

    @staticmethod
    def _get_groww_api_class():
        # Lazy SDK import to keep other brokers decoupled from Groww dependency.
        try:
            from growwapi import GrowwAPI
        except ModuleNotFoundError as error:
            raise ModuleNotFoundError(
                "Groww SDK not installed. Open CLI Settings -> Broker SDKs and install Groww SDK."
            ) from error

        return GrowwAPI

    def _get_client(self):
        token = self.authenticate()
        groww_api = self._get_groww_api_class()
        return groww_api(token)

    def _map_exchange(self, groww_client, exchange: str | None):
        if exchange and exchange.upper() == "BSE":
            return groww_client.EXCHANGE_BSE
        return groww_client.EXCHANGE_NSE

    def _map_segment(self, groww_client, segment: str | None):
        if segment and segment.upper() in {"FUTURES", "FNO"}:
            return groww_client.SEGMENT_FNO
        return groww_client.SEGMENT_CASH

    @staticmethod
    def _generate_order_reference_id() -> str:
        length = secrets.randbelow(13) + 8
        chars = string.ascii_letters + string.digits
        return "".join(secrets.choice(chars) for _ in range(length))

    def authenticate(self) -> str:
        try:
            if self.groww_auth_token:
                return self.groww_auth_token

            if not self.groww_api_key or not self.groww_api_secret:
                msg = "GROWW_API_KEY or GROWW_API_SECRET is missing."
                logging.error(msg)
                raise CustomException(msg, sys)

            try:
                import pyotp
            except ModuleNotFoundError as error:
                raise ModuleNotFoundError(
                    "pyotp is missing for Groww authentication. Install Groww SDK from CLI Settings."
                ) from error

            totp = pyotp.TOTP(self.groww_api_secret).now()
            groww_api = self._get_groww_api_class()
            access_token = groww_api.get_access_token(api_key=self.groww_api_key, totp=totp)
            if not access_token:
                msg = "Groww returned an empty access token."
                logging.error(msg)
                raise CustomException(msg, sys)

            self.groww_auth_token = access_token
            os.environ["GROWW_ACCESS_TOKEN"] = access_token
            set_groww_access_token(access_token)
            logging.info("Groww access token generated successfully.")
            return access_token
        except CustomException:
            raise
        except Exception as e:
            raise CustomException(e, sys) from e

    def place_order(
        self,
        trading_symbol: str,
        quantity: int,
        price: float,
        exchange: str = "NSE",
        segment: str = "CASH",
        transaction_type: str = "BUY",
    ) -> Any:
        try:
            groww = self._get_client()
            if transaction_type.upper() == "SELL":
                mapped_transaction_type = groww.TRANSACTION_TYPE_SELL
            else:
                mapped_transaction_type = groww.TRANSACTION_TYPE_BUY
            return groww.place_order(
                trading_symbol=trading_symbol.upper(),
                quantity=quantity,
                price=price,
                validity=groww.VALIDITY_DAY,
                segment=self._map_segment(groww, segment),
                product=groww.PRODUCT_CNC,
                exchange=self._map_exchange(groww, exchange),
                order_type=groww.ORDER_TYPE_LIMIT,
                transaction_type=mapped_transaction_type,
                trigger_price=None,
                order_reference_id=self._generate_order_reference_id(),
            )
        except Exception as e:
            raise CustomException(e, sys) from e

    def modify_order(
        self,
        order_id: str,
        quantity: int,
        price: float,
        segment: str = "CASH",
    ) -> Any:
        try:
            groww = self._get_client()
            return groww.modify_order(
                groww_order_id=order_id,
                quantity=quantity,
                price=price,
                segment=self._map_segment(groww, segment),
                order_type=groww.ORDER_TYPE_LIMIT,
            )
        except Exception as e:
            raise CustomException(e, sys) from e

    def cancel_order(self, order_id: str, segment: str = "CASH") -> Any:
        try:
            groww = self._get_client()
            return groww.cancel_order(
                groww_order_id=order_id,
                segment=self._map_segment(groww, segment),
            )
        except Exception as e:
            raise CustomException(e, sys) from e

    def get_order_list(
        self,
        segment: str = "CASH",
        page: int = 0,
        page_size: int = 10,
    ) -> Any:
        try:
            groww = self._get_client()
            return groww.get_order_list(
                segment=self._map_segment(groww, segment),
                page=page,
                page_size=page_size,
            )
        except Exception as e:
            raise CustomException(e, sys) from e

    def get_order_status(self, order_id: str, segment: str = "CASH") -> Any:
        try:
            groww = self._get_client()
            return groww.get_order_status(
                groww_order_id=order_id,
                segment=self._map_segment(groww, segment),
            )
        except Exception as e:
            raise CustomException(e, sys) from e

    def get_order_details(self, order_id: str, segment: str = "CASH") -> Any:
        try:
            groww = self._get_client()
            return groww.get_order_detail(
                groww_order_id=order_id,
                segment=self._map_segment(groww, segment),
            )
        except Exception as e:
            raise CustomException(e, sys) from e

    def get_trades_details(
        self,
        order_id: str,
        segment: str = "CASH",
        page: int = 0,
        page_size: int = 10,
    ) -> Any:
        try:
            groww = self._get_client()
            return groww.get_trade_list_for_order(
                groww_order_id=order_id,
                segment=self._map_segment(groww, segment),
                page=page,
                page_size=page_size,
            )
        except Exception as e:
            raise CustomException(e, sys) from e

    def get_portfolio(self) -> Any:
        try:
            groww = self._get_client()
            return groww.get_holdings_for_user(timeout=5)
        except Exception as e:
            raise CustomException(e, sys) from e

    def get_positions(self, segment: str | None = None) -> Any:
        try:
            groww = self._get_client()
            if segment:
                return groww.get_positions_for_user(segment=self._map_segment(groww, segment), timeout=5)
            return groww.get_positions_for_user()
        except Exception as e:
            raise CustomException(e, sys) from e

    def get_quote(
        self,
        trading_symbol: str,
        exchange: str = "NSE",
        segment: str = "CASH",
    ) -> Any:
        try:
            groww = self._get_client()
            return groww.get_quote(
                trading_symbol=trading_symbol.upper(),
                exchange=self._map_exchange(groww, exchange),
                segment=self._map_segment(groww, segment),
                timeout=5,
            )
        except Exception as e:
            raise CustomException(e, sys) from e

    def get_ltp(
        self,
        trading_symbol: str,
        exchange: str = "NSE",
        segment: str = "CASH",
    ) -> Any:
        try:
            groww = self._get_client()
            symbol = trading_symbol.upper()
            if exchange and exchange.upper() == "NSE":
                symbol = f"NSE_{symbol}"
            elif exchange and exchange.upper() == "BSE":
                symbol = f"BSE_{symbol}"

            return groww.get_ltp(
                exchange_trading_symbols=symbol,
                segment=self._map_segment(groww, segment),
                timeout=5,
            )
        except Exception as e:
            raise CustomException(e, sys) from e

    def search_instrument(self, symbol: str, exchange: str | None = None) -> Any:
        try:
            groww = self._get_client()
            normalized = symbol.upper()
            symbols_to_try = []

            if exchange:
                exchange_upper = exchange.upper()
                if exchange_upper in {"NSE", "BSE"}:
                    symbols_to_try.append(f"{exchange_upper}-{normalized}")
            symbols_to_try.append(normalized)

            for candidate in symbols_to_try:
                try:
                    result = groww.get_instrument_by_groww_symbol(groww_symbol=candidate)
                    if result is not None:
                        return result
                except Exception:
                    continue

            exchange_info = f" on {exchange}" if exchange else ""
            msg = f"Instrument not found for symbol '{normalized}'{exchange_info}."
            raise CustomException(msg, sys)
        except CustomException:
            raise
        except Exception as e:
            raise CustomException(e, sys) from e


