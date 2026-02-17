class PositionSizer:
    """Risk-based position sizing."""

    @staticmethod
    def calculate_quantity(
        cash: float,
        price: float,
        risk_per_trade_pct: float,
        stop_loss_pct: float,
        max_position_pct: float,
        capital_base: float,
    ) -> int:
        if price <= 0 or cash <= 0:
            return 0

        safe_stop_loss = max(stop_loss_pct, 0.001)
        risk_budget = capital_base * max(risk_per_trade_pct, 0.001)
        max_position_budget = capital_base * max(max_position_pct, 0.01)

        qty_by_risk = int(risk_budget / (price * safe_stop_loss))
        qty_by_allocation = int(max_position_budget / price)
        qty_by_cash = int(cash / price)

        return max(0, min(qty_by_risk, qty_by_allocation, qty_by_cash))


