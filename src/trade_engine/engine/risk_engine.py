from dataclasses import dataclass
from typing import Tuple


@dataclass
class RiskConfig:
    initial_capital: float = 100000.0
    max_daily_loss_pct: float = 0.03
    max_position_pct: float = 0.10
    risk_per_trade_pct: float = 0.01
    stop_loss_pct: float = 0.02
    take_profit_pct: float = 0.04
    buy_enabled: bool = True
    sell_enabled: bool = True


class RiskEngine:
    """Simple pre-trade and in-trade risk checks for CLI runtime."""

    def __init__(self, config: RiskConfig):
        self.config = config

    def is_signal_enabled(self, signal: int) -> bool:
        if signal == 1:
            return self.config.buy_enabled
        if signal == -1:
            return self.config.sell_enabled
        return True

    def can_open_position(
        self,
        cash: float,
        current_exposure: float,
        entry_price: float,
        quantity: int,
    ) -> Tuple[bool, str]:
        if quantity <= 0:
            return False, "Quantity is zero."

        notional = entry_price * quantity
        max_notional = self.config.initial_capital * self.config.max_position_pct
        if notional > max_notional:
            return False, f"Position size exceeds max allocation ({self.config.max_position_pct:.0%})."

        if notional > cash:
            return False, "Insufficient cash for position."

        projected_exposure = current_exposure + notional
        if projected_exposure > self.config.initial_capital:
            return False, "Projected exposure exceeds total capital."

        return True, "OK"

    def daily_loss_breached(self, realized_pnl: float) -> bool:
        max_loss_abs = self.config.initial_capital * self.config.max_daily_loss_pct
        return realized_pnl <= -abs(max_loss_abs)

    def check_exit(
        self,
        entry_price: float,
        current_price: float,
    ) -> Tuple[bool, str]:
        if entry_price <= 0:
            return False, "NONE"

        drawdown = (current_price - entry_price) / entry_price
        if drawdown <= -abs(self.config.stop_loss_pct):
            return True, "STOP_LOSS"
        if drawdown >= abs(self.config.take_profit_pct):
            return True, "TAKE_PROFIT"
        return False, "NONE"

    def check_exit_short(
        self,
        entry_price: float,
        current_price: float,
    ) -> Tuple[bool, str]:
        if entry_price <= 0:
            return False, "NONE"

        move = (entry_price - current_price) / entry_price
        if move <= -abs(self.config.stop_loss_pct):
            return True, "STOP_LOSS"
        if move >= abs(self.config.take_profit_pct):
            return True, "TAKE_PROFIT"
        return False, "NONE"


