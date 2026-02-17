from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotext as plt


@dataclass
class BacktestCostModel:
    commission_pct: float = 0.001
    slippage_bps: float = 5.0
    latency_bars: int = 0
    borrow_cost_pct_annual: float = 0.0


class Backtester:
    """Backtest a strategy on historical OHLCV data."""

    @staticmethod
    def _execution_index(i: int, last_idx: int, latency_bars: int) -> int:
        return min(last_idx, i + max(0, int(latency_bars)))

    @staticmethod
    def _entry_price(raw_price: float, slippage_bps: float) -> float:
        return raw_price * (1.0 + max(0.0, slippage_bps) / 10000.0)

    @staticmethod
    def _exit_price(raw_price: float, slippage_bps: float) -> float:
        return raw_price * (1.0 - max(0.0, slippage_bps) / 10000.0)

    def run_backtest(self, df, strategy, initial_capital=100000, cost_model: BacktestCostModel | None = None):
        if hasattr(strategy, "combine_signals"):
            df = strategy.combine_signals(df)
        else:
            df = strategy.calculate_signals(df)

        model = cost_model or BacktestCostModel()
        commission = max(0.0, float(model.commission_pct))
        slippage_bps = max(0.0, float(model.slippage_bps))
        latency = max(0, int(model.latency_bars))

        capital = float(initial_capital)
        position = 0
        entry_price = 0.0
        entry_date = None
        trade_log = []
        equity_curve = []
        total_fees = 0.0
        total_slippage = 0.0
        total_borrow = 0.0

        closes = df["Close"].tolist()
        signals = df["signal"].tolist()
        dates = list(df.index)
        last_idx = len(df) - 1

        for i in range(len(df)):
            signal = signals[i]

            if signal == 1 and position == 0:
                exec_i = self._execution_index(i, last_idx, latency)
                raw = float(closes[exec_i])
                price = self._entry_price(raw, slippage_bps)
                shares = int(capital / (price * (1 + commission)))
                if shares > 0:
                    gross = shares * price
                    fees = gross * commission
                    slippage_cost = shares * (price - raw)
                    cost = gross + fees
                    capital -= cost
                    total_fees += fees
                    total_slippage += slippage_cost
                    position = shares
                    entry_price = price
                    entry_date = dates[exec_i]
                    trade_log.append(
                        {
                            "date": str(dates[exec_i]),
                            "action": "BUY",
                            "price": round(price, 4),
                            "raw_price": round(raw, 4),
                            "shares": shares,
                            "fees": round(fees, 2),
                            "slippage_cost": round(slippage_cost, 2),
                            "capital": round(capital, 2),
                        }
                    )

            elif signal == -1 and position > 0:
                exec_i = self._execution_index(i, last_idx, latency)
                raw = float(closes[exec_i])
                price = self._exit_price(raw, slippage_bps)
                gross = position * price
                fees = gross * commission
                revenue = gross - fees
                slippage_cost = position * (raw - price)

                borrow_cost = 0.0
                if model.borrow_cost_pct_annual > 0 and entry_date is not None:
                    try:
                        days_held = max(1, int((dates[exec_i] - entry_date).days))
                    except Exception:
                        days_held = 1
                    borrow_cost = gross * (model.borrow_cost_pct_annual / 365.0) * days_held
                    revenue -= borrow_cost

                pnl = revenue - (position * entry_price * (1 + commission))
                capital += revenue
                total_fees += fees
                total_slippage += slippage_cost
                total_borrow += borrow_cost

                trade_log.append(
                    {
                        "date": str(dates[exec_i]),
                        "action": "SELL",
                        "price": round(price, 4),
                        "raw_price": round(raw, 4),
                        "shares": position,
                        "fees": round(fees, 2),
                        "slippage_cost": round(slippage_cost, 2),
                        "borrow_cost": round(borrow_cost, 2),
                        "pnl": round(pnl, 2),
                        "capital": round(capital, 2),
                    }
                )
                position = 0
                entry_price = 0.0
                entry_date = None

            mark_price = float(closes[i])
            portfolio_value = capital + position * mark_price
            equity_curve.append(portfolio_value)

        if position > 0:
            raw = float(closes[-1])
            price = self._exit_price(raw, slippage_bps)
            gross = position * price
            fees = gross * commission
            revenue = gross - fees
            capital += revenue
            total_fees += fees
            total_slippage += position * (raw - price)
            position = 0

        final_value = capital
        total_return = ((final_value - initial_capital) / initial_capital) * 100

        sells = [t for t in trade_log if t["action"] == "SELL"]
        wins = [t for t in sells if t.get("pnl", 0) > 0]
        win_rate = (len(wins) / len(sells) * 100) if sells else 0

        equity = pd.Series(equity_curve)
        peak = equity.cummax()
        drawdown = (equity - peak) / peak
        max_drawdown = drawdown.min() * 100 if len(drawdown) > 0 else 0

        if len(equity) > 1:
            returns = equity.pct_change().dropna()
            sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() != 0 else 0
        else:
            sharpe_ratio = 0

        total_costs = total_fees + total_slippage + total_borrow
        return {
            "total_return": round(total_return, 2),
            "final_value": round(final_value, 2),
            "initial_capital": initial_capital,
            "win_rate": round(win_rate, 2),
            "max_drawdown": round(max_drawdown, 2),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "total_trades": len(sells),
            "total_fees": round(total_fees, 2),
            "total_slippage": round(total_slippage, 2),
            "total_borrow_cost": round(total_borrow, 2),
            "total_costs": round(total_costs, 2),
            "trade_log": trade_log,
            "equity_curve": equity_curve,
            "cost_model": {
                "commission_pct": model.commission_pct,
                "slippage_bps": model.slippage_bps,
                "latency_bars": model.latency_bars,
                "borrow_cost_pct_annual": model.borrow_cost_pct_annual,
            },
        }

    def plot_equity_curve(self, results):
        equity = results.get("equity_curve", [])
        if not equity:
            return
        plt.clear_figure()
        plt.theme("dark")
        plt.title("Equity Curve")
        plt.xlabel("Trading Days")
        plt.ylabel("Portfolio Value")
        plt.plot(list(range(len(equity))), equity, label="Equity")
        plt.hline(results["initial_capital"], "red")
        plt.show()
