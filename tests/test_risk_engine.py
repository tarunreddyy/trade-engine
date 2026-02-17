from datetime import datetime

from trade_engine.engine.risk_engine import RiskConfig, RiskEngine


def test_pre_order_guard_blocks_kill_switch_for_entries():
    config = RiskConfig(kill_switch_enabled=True, market_hours_only=False, max_orders_per_day=10)
    engine = RiskEngine(config)

    allowed, reason = engine.pre_order_guard(mode="live", orders_today=0, is_exit=False)
    assert not allowed
    assert reason == "kill_switch_enabled"

    allowed_exit, reason_exit = engine.pre_order_guard(mode="live", orders_today=0, is_exit=True)
    assert allowed_exit
    assert reason_exit == "ok"


def test_pre_order_guard_enforces_max_orders_per_day():
    config = RiskConfig(kill_switch_enabled=False, market_hours_only=False, max_orders_per_day=2)
    engine = RiskEngine(config)

    allowed, reason = engine.pre_order_guard(mode="live", orders_today=2, is_exit=False)
    assert not allowed
    assert reason == "max_orders_per_day_reached"


def test_market_hours_check():
    config = RiskConfig(kill_switch_enabled=False, market_hours_only=True, max_orders_per_day=5)
    engine = RiskEngine(config)

    during_market_utc = datetime(2026, 1, 5, 4, 0, 0)  # 09:30 IST Monday
    outside_market_utc = datetime(2026, 1, 5, 12, 0, 0)  # 17:30 IST Monday
    weekend_utc = datetime(2026, 1, 4, 4, 0, 0)  # Sunday

    assert engine.is_market_open(during_market_utc)
    assert not engine.is_market_open(outside_market_utc)
    assert not engine.is_market_open(weekend_utc)
