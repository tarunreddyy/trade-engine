import pytest

from trade_engine.brokers.broker_factory import BrokerFactory
from trade_engine.config.broker_config import set_active_broker


def test_broker_factory_uses_settings_active_broker():
    set_active_broker("upstox")
    broker = BrokerFactory.create_broker()
    assert broker.__class__.__name__ == "UpstoxBroker"

    set_active_broker("zerodha")
    broker = BrokerFactory.create_broker()
    assert broker.__class__.__name__ == "ZerodhaBroker"


def test_broker_factory_rejects_unknown_broker():
    with pytest.raises(ValueError):
        BrokerFactory.create_broker("does-not-exist")
