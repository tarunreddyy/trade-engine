import pandas as pd

from trade_engine.strategies.backtester import BacktestCostModel, Backtester


class SimpleStrategy:
    def calculate_signals(self, df):
        df = df.copy()
        df["signal"] = 0
        df.loc[df.index[0], "signal"] = 1
        df.loc[df.index[-1], "signal"] = -1
        return df


def _sample_df():
    return pd.DataFrame(
        {
            "Open": [100, 101, 102, 103, 104],
            "High": [101, 102, 103, 104, 105],
            "Low": [99, 100, 101, 102, 103],
            "Close": [100, 101, 102, 103, 104],
            "Volume": [1000, 1000, 1000, 1000, 1000],
        },
        index=pd.date_range("2026-01-01", periods=5, freq="D"),
    )


def test_backtester_cost_model_reduces_returns():
    df = _sample_df()
    strategy = SimpleStrategy()
    backtester = Backtester()

    no_cost = backtester.run_backtest(
        df,
        strategy,
        initial_capital=100000,
        cost_model=BacktestCostModel(commission_pct=0.0, slippage_bps=0.0, latency_bars=0),
    )
    with_cost = backtester.run_backtest(
        df,
        strategy,
        initial_capital=100000,
        cost_model=BacktestCostModel(commission_pct=0.002, slippage_bps=10.0, latency_bars=1),
    )

    assert with_cost["final_value"] < no_cost["final_value"]
    assert with_cost["total_costs"] > 0
