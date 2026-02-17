from trade_engine.engine.execution_router import ExecutionRouter
from trade_engine.engine.risk_engine import RiskConfig, RiskEngine


class DummyBroker:
    def place_order(self, **kwargs):
        return {"ok": True, "payload": kwargs}


def test_router_respects_max_orders_per_day():
    risk = RiskEngine(
        RiskConfig(
            kill_switch_enabled=False,
            market_hours_only=False,
            max_orders_per_day=1,
        )
    )
    router = ExecutionRouter(mode="live", broker=DummyBroker(), risk_engine=risk)

    first = router.route_order(symbol="TCS.NS", side="BUY", quantity=1, price=100.0)
    second = router.route_order(symbol="INFY.NS", side="BUY", quantity=1, price=100.0)

    assert first["status"] == "SENT"
    assert second["status"] == "REJECTED"
    assert second["reason"] == "max_orders_per_day_reached"


def test_router_respects_kill_switch():
    risk = RiskEngine(
        RiskConfig(
            kill_switch_enabled=True,
            market_hours_only=False,
            max_orders_per_day=10,
        )
    )
    router = ExecutionRouter(mode="live", broker=DummyBroker(), risk_engine=risk)

    blocked = router.route_order(symbol="RELIANCE.NS", side="BUY", quantity=1, price=100.0)
    assert blocked["status"] == "REJECTED"
    assert blocked["reason"] == "kill_switch_enabled"

    exit_allowed = router.route_order(symbol="RELIANCE.NS", side="SELL", quantity=1, price=100.0, is_exit=True)
    assert exit_allowed["status"] == "SENT"
