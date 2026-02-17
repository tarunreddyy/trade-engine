import pandas as pd

from trade_engine.engine.walk_forward import WalkForwardEvaluator


class SignalStrategy:
    def calculate_signals(self, df):
        df = df.copy()
        df["signal"] = 0
        df.loc[df.index[::10], "signal"] = 1
        df.loc[df.index[5::10], "signal"] = -1
        return df


def test_walk_forward_evaluator_returns_oos_metrics():
    rows = 180
    df = pd.DataFrame(
        {
            "Open": [100 + i * 0.1 for i in range(rows)],
            "High": [101 + i * 0.1 for i in range(rows)],
            "Low": [99 + i * 0.1 for i in range(rows)],
            "Close": [100 + i * 0.1 for i in range(rows)],
            "Volume": [100000] * rows,
        },
        index=pd.date_range("2025-01-01", periods=rows, freq="D"),
    )

    evaluator = WalkForwardEvaluator()
    result = evaluator.evaluate(df=df, strategy=SignalStrategy(), initial_capital=100000, windows=3)

    assert result is not None
    assert result["oos_windows"] >= 1
    assert "total_return" in result
