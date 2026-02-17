from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional, Tuple
from zoneinfo import ZoneInfo


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
    kill_switch_enabled: bool = False
    market_hours_only: bool = True
    max_orders_per_day: int = 40


class RiskEngine:
    """Pre-trade and in-trade risk checks for CLI runtime."""

    IST_ZONE = "Asia/Kolkata"
    MARKET_OPEN = time(9, 15)
    MARKET_CLOSE = time(15, 30)

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

    def check_exit(self, entry_price: float, current_price: float) -> Tuple[bool, str]:
        if entry_price <= 0:
            return False, "NONE"

        drawdown = (current_price - entry_price) / entry_price
        if drawdown <= -abs(self.config.stop_loss_pct):
            return True, "STOP_LOSS"
        if drawdown >= abs(self.config.take_profit_pct):
            return True, "TAKE_PROFIT"
        return False, "NONE"

    def check_exit_short(self, entry_price: float, current_price: float) -> Tuple[bool, str]:
        if entry_price <= 0:
            return False, "NONE"

        move = (entry_price - current_price) / entry_price
        if move <= -abs(self.config.stop_loss_pct):
            return True, "STOP_LOSS"
        if move >= abs(self.config.take_profit_pct):
            return True, "TAKE_PROFIT"
        return False, "NONE"

    def is_market_open(self, now_utc: Optional[datetime] = None) -> bool:
        now_utc = now_utc or datetime.utcnow()
        now_ist = now_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(self.IST_ZONE))
        if now_ist.weekday() >= 5:
            return False
        local_time = now_ist.time()
        return self.MARKET_OPEN <= local_time <= self.MARKET_CLOSE

    def pre_order_guard(
        self,
        mode: str,
        orders_today: int,
        is_exit: bool = False,
        now_utc: Optional[datetime] = None,
    ) -> Tuple[bool, str]:
        if self.config.kill_switch_enabled and not is_exit:
            return False, "kill_switch_enabled"

        if mode != "live":
            return True, "ok"

        if self.config.market_hours_only and not self.is_market_open(now_utc=now_utc):
            return False, "outside_market_hours"

        if not is_exit and orders_today >= max(1, int(self.config.max_orders_per_day)):
            return False, "max_orders_per_day_reached"

        return True, "ok"
