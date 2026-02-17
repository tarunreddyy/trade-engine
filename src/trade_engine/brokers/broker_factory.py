from importlib import import_module
from typing import Dict, Type

from trade_engine.brokers.base_broker import BaseBroker
from trade_engine.config.broker_config import get_active_broker


class BrokerFactory:
    """Factory to create broker adapters based on configuration."""

    _broker_registry: Dict[str, str] = {}

    @classmethod
    def _register_default_brokers(cls):
        if cls._broker_registry:
            return
        cls._broker_registry = {
            "groww": "trade_engine.brokers.groww_broker.GrowwBroker",
            "upstox": "trade_engine.brokers.upstox_broker.UpstoxBroker",
            "zerodha": "trade_engine.brokers.zerodha_broker.ZerodhaBroker",
        }

    @classmethod
    def _load_broker_class(cls, broker_name: str) -> Type[BaseBroker]:
        broker_path = cls._broker_registry[broker_name]
        module_name, class_name = broker_path.rsplit(".", 1)
        module = import_module(module_name)
        return getattr(module, class_name)

    @classmethod
    def create_broker(cls, broker_name: str = "") -> BaseBroker:
        cls._register_default_brokers()
        selected_broker = (broker_name or get_active_broker()).strip().lower()
        if selected_broker not in cls._broker_registry:
            supported = ", ".join(sorted(cls._broker_registry.keys()))
            raise ValueError(f"Unknown broker '{selected_broker}'. Supported brokers: {supported}")

        broker_cls = cls._load_broker_class(selected_broker)
        return broker_cls()


