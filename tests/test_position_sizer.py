from trade_engine.engine.position_sizer import PositionSizer


def test_position_sizer_returns_zero_for_invalid_inputs():
    assert PositionSizer.calculate_quantity(0, 100, 0.01, 0.02, 0.1, 100000) == 0
    assert PositionSizer.calculate_quantity(100000, 0, 0.01, 0.02, 0.1, 100000) == 0


def test_position_sizer_limits_by_risk_allocation_and_cash():
    qty = PositionSizer.calculate_quantity(
        cash=10000,
        price=100,
        risk_per_trade_pct=0.01,
        stop_loss_pct=0.02,
        max_position_pct=0.1,
        capital_base=100000,
    )
    # By risk = 500, by allocation = 100, by cash = 100 -> 100
    assert qty == 100
