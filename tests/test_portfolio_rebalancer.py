from trade_engine.engine.portfolio_rebalancer import PortfolioRebalancer


def test_parse_target_weights():
    parsed = PortfolioRebalancer.parse_target_weights("RELIANCE.NS=25,TCS.NS=20,INVALID,INFY.NS=15")
    assert parsed["RELIANCE.NS"] == 0.25
    assert parsed["TCS.NS"] == 0.20
    assert parsed["INFY.NS"] == 0.15
    assert "INVALID" not in parsed


def test_create_rebalance_plan_generates_actions():
    rebalancer = PortfolioRebalancer()
    portfolio_state = {
        "cash": 20000.0,
        "equity": 100000.0,
        "positions": [
            {
                "symbol": "RELIANCE.NS",
                "quantity": 200,
                "entry_price": 100.0,
                "market_price": 100.0,
                "market_value": 20000.0,
                "side": "LONG",
            }
        ],
    }
    prices = {"RELIANCE.NS": 100.0, "TCS.NS": 200.0}
    targets = {"RELIANCE.NS": 0.10, "TCS.NS": 0.30}

    plan = rebalancer.create_rebalance_plan(
        portfolio_state=portfolio_state,
        prices=prices,
        target_weights=targets,
        drift_threshold_pct=1.0,
    )

    actions = plan["actions"]
    assert len(actions) >= 1
    symbols = {a["symbol"] for a in actions}
    assert "RELIANCE.NS" in symbols or "TCS.NS" in symbols
