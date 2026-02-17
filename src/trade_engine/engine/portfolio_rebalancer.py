from typing import Dict, List, Optional


class PortfolioRebalancer:
    """Computes drift and order suggestions to rebalance portfolio weights."""

    @staticmethod
    def parse_target_weights(raw: str) -> Dict[str, float]:
        """
        Parse input like: RELIANCE.NS=25,TCS.NS=20,INFY.NS=15
        Returns decimals: {"RELIANCE.NS": 0.25, ...}
        """
        weights: Dict[str, float] = {}
        if not raw.strip():
            return weights
        for chunk in raw.split(","):
            if "=" not in chunk:
                continue
            symbol, value = chunk.split("=", 1)
            symbol = symbol.strip().upper()
            if not symbol:
                continue
            try:
                pct = float(value.strip())
            except ValueError:
                continue
            weights[symbol] = pct / 100.0
        return weights

    @staticmethod
    def _normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
        if not weights:
            return {}
        total = sum(max(weight, 0.0) for weight in weights.values())
        if total <= 0:
            return {}
        if total <= 1.0:
            return {symbol: max(weight, 0.0) for symbol, weight in weights.items()}
        return {symbol: max(weight, 0.0) / total for symbol, weight in weights.items()}

    def create_rebalance_plan(
        self,
        portfolio_state: dict,
        prices: Dict[str, float],
        target_weights: Dict[str, float],
        drift_threshold_pct: float = 2.0,
    ) -> dict:
        drift_threshold = abs(drift_threshold_pct) / 100.0
        normalized_targets = self._normalize_weights(target_weights)
        cash = float(portfolio_state.get("cash", 0.0))
        equity = float(portfolio_state.get("equity", 0.0))
        if equity <= 0:
            return {
                "equity": equity,
                "cash": cash,
                "summary": "No equity available for rebalancing.",
                "actions": [],
                "allocations": [],
            }

        current_values: Dict[str, float] = {}
        for pos in portfolio_state.get("positions", []):
            symbol = str(pos.get("symbol", "")).upper()
            if not symbol:
                continue
            market_value = float(pos.get("market_value", 0.0))
            current_values[symbol] = current_values.get(symbol, 0.0) + market_value

        symbols = sorted(set(current_values.keys()) | set(normalized_targets.keys()))
        allocations: List[dict] = []
        actions: List[dict] = []
        available_cash = cash

        for symbol in symbols:
            price = float(prices.get(symbol, 0.0) or 0.0)
            current_value = float(current_values.get(symbol, 0.0))
            target_weight = float(normalized_targets.get(symbol, 0.0))
            target_value = equity * target_weight
            current_weight = current_value / equity
            drift = current_weight - target_weight
            delta_value = target_value - current_value

            allocations.append(
                {
                    "symbol": symbol,
                    "current_weight_pct": round(current_weight * 100, 2),
                    "target_weight_pct": round(target_weight * 100, 2),
                    "drift_pct": round(drift * 100, 2),
                    "current_value": round(current_value, 2),
                    "target_value": round(target_value, 2),
                }
            )

            if price <= 0:
                continue
            if abs(drift) < drift_threshold:
                continue

            if delta_value > 0:
                qty = int(delta_value / price)
                if qty <= 0:
                    continue
                max_affordable = int(max(0.0, available_cash) / price)
                qty = min(qty, max_affordable)
                if qty <= 0:
                    continue
                notional = qty * price
                available_cash -= notional
                actions.append(
                    {
                        "symbol": symbol,
                        "action": "BUY",
                        "quantity": qty,
                        "price": round(price, 2),
                        "notional": round(notional, 2),
                        "reason": "Drift correction to target weight",
                    }
                )
            elif delta_value < 0:
                qty = int(abs(delta_value) / price)
                if qty <= 0:
                    continue
                notional = qty * price
                available_cash += notional
                actions.append(
                    {
                        "symbol": symbol,
                        "action": "SELL",
                        "quantity": qty,
                        "price": round(price, 2),
                        "notional": round(notional, 2),
                        "reason": "Drift correction to target weight",
                    }
                )

        return {
            "equity": round(equity, 2),
            "cash": round(cash, 2),
            "projected_cash_after_actions": round(available_cash, 2),
            "drift_threshold_pct": round(drift_threshold * 100, 2),
            "allocations": allocations,
            "actions": actions,
            "summary": f"Generated {len(actions)} rebalance actions.",
        }

    @staticmethod
    def latest_prices_from_rows(rows: List[dict]) -> Dict[str, float]:
        prices: Dict[str, float] = {}
        for row in rows:
            symbol = str(row.get("symbol", "")).upper()
            price = row.get("price")
            if symbol and price is not None:
                try:
                    prices[symbol] = float(price)
                except (TypeError, ValueError):
                    continue
        return prices

    def execute_plan(self, console, actions: List[dict]) -> List[dict]:
        """Execute rebalance actions through live console order router."""
        results: List[dict] = []
        for action in actions:
            result = console.execute_manual_order(
                symbol=action["symbol"],
                side=action["action"],
                quantity=int(action["quantity"]),
                price=float(action["price"]),
                reason="REBALANCE",
            )
            merged = dict(action)
            merged["execution"] = result
            results.append(merged)
        return results


