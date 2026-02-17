import pandas as pd
import numpy as np
import plotext as plt
from trade_engine.strategies.base_strategy import BaseStrategy


class Backtester:
    """Backtest a strategy on historical OHLCV data."""

    def run_backtest(self, df, strategy, initial_capital=100000, commission=0.001):
        """Run backtest and return performance metrics.

        Args:
            df: DataFrame with OHLCV data.
            strategy: A BaseStrategy instance (or StrategyCombiner with combine_signals).
            initial_capital: Starting capital.
            commission: Per-trade commission rate.

        Returns:
            dict with total_return, win_rate, max_drawdown, sharpe_ratio, trade_log.
        """
        if hasattr(strategy, "combine_signals"):
            df = strategy.combine_signals(df)
        else:
            df = strategy.calculate_signals(df)

        capital = initial_capital
        position = 0  # number of shares held
        entry_price = 0
        trade_log = []
        equity_curve = []

        for i in range(len(df)):
            price = df["Close"].iloc[i]
            signal = df["signal"].iloc[i]
            date = df.index[i]

            if signal == 1 and position == 0:
                # Buy
                shares = int(capital / (price * (1 + commission)))
                if shares > 0:
                    cost = shares * price * (1 + commission)
                    capital -= cost
                    position = shares
                    entry_price = price
                    trade_log.append({
                        "date": str(date),
                        "action": "BUY",
                        "price": round(price, 2),
                        "shares": shares,
                        "capital": round(capital, 2),
                    })
            elif signal == -1 and position > 0:
                # Sell
                revenue = position * price * (1 - commission)
                pnl = revenue - (position * entry_price * (1 + commission))
                capital += revenue
                trade_log.append({
                    "date": str(date),
                    "action": "SELL",
                    "price": round(price, 2),
                    "shares": position,
                    "pnl": round(pnl, 2),
                    "capital": round(capital, 2),
                })
                position = 0

            # Track equity
            portfolio_value = capital + position * price
            equity_curve.append(portfolio_value)

        # Close any open position at last price
        if position > 0:
            last_price = df["Close"].iloc[-1]
            revenue = position * last_price * (1 - commission)
            capital += revenue
            position = 0

        final_value = capital
        total_return = ((final_value - initial_capital) / initial_capital) * 100

        # Win rate
        sells = [t for t in trade_log if t["action"] == "SELL"]
        wins = [t for t in sells if t.get("pnl", 0) > 0]
        win_rate = (len(wins) / len(sells) * 100) if sells else 0

        # Max drawdown
        equity = pd.Series(equity_curve)
        peak = equity.cummax()
        drawdown = (equity - peak) / peak
        max_drawdown = drawdown.min() * 100 if len(drawdown) > 0 else 0

        # Sharpe ratio (annualized, assuming daily data)
        if len(equity) > 1:
            returns = equity.pct_change().dropna()
            if returns.std() != 0:
                sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252)
            else:
                sharpe_ratio = 0
        else:
            sharpe_ratio = 0

        return {
            "total_return": round(total_return, 2),
            "final_value": round(final_value, 2),
            "initial_capital": initial_capital,
            "win_rate": round(win_rate, 2),
            "max_drawdown": round(max_drawdown, 2),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "total_trades": len(sells),
            "trade_log": trade_log,
            "equity_curve": equity_curve,
        }

    def plot_equity_curve(self, results):
        """Plot the equity curve in terminal."""
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


