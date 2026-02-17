import pandas as pd

from trade_engine.engine.strategy_leaderboard import StrategyLeaderboard


def _sample_df():
    rows = 120
    return pd.DataFrame(
        {
            "Open": [100 + i * 0.1 for i in range(rows)],
            "High": [101 + i * 0.1 for i in range(rows)],
            "Low": [99 + i * 0.1 for i in range(rows)],
            "Close": [100 + i * 0.1 for i in range(rows)],
            "Volume": [100000] * rows,
        }
    )


def test_strategy_leaderboard_build_with_monkeypatched_data(monkeypatch):
    leaderboard = StrategyLeaderboard(max_workers=2)
    sample = _sample_df()

    def fake_fetch(symbol, period, interval):
        return symbol, sample

    def fake_eval(self, strategy_name, symbol, df, initial_capital, oos_only=False, walk_forward_windows=3):
        return {
            "strategy": strategy_name,
            "symbol": symbol,
            "score": 10.0 if symbol.endswith("A") else 5.0,
            "evaluation_mode": "oos" if oos_only else "full_history",
            "total_return_pct": 12.0,
            "sharpe_ratio": 1.1,
            "max_drawdown_pct": -4.0,
            "win_rate_pct": 55.0,
            "trades": 10,
            "final_value": 112000.0,
            "total_costs": 120.0,
            "oos_windows": walk_forward_windows if oos_only else 0,
            "category": "Trend",
            "risk_profile": "medium",
            "preferred_timeframe": "1d",
        }

    monkeypatch.setattr(StrategyLeaderboard, "_fetch_history", staticmethod(fake_fetch))
    monkeypatch.setattr(StrategyLeaderboard, "_evaluate_pair", fake_eval)

    result = leaderboard.build(["SYMA", "SYMB"], top_n=5)
    assert result["symbols_scanned"] == 2
    assert result["pair_count"] > 0
    assert len(result["rows"]) <= 5
    assert len(result["strategy_summary"]) > 0
