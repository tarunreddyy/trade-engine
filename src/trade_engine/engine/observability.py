import json
from datetime import datetime
from pathlib import Path


class RuntimeMetrics:
    """Collects and exports runtime metrics snapshots to JSON."""

    def __init__(self, output_file: str = "data/runtime/metrics_latest.json"):
        self.output_file = output_file
        self.max_equity = 0.0
        self.min_equity = float("inf")
        self.total_orders = 0
        self.filled_orders = 0
        self.rejected_orders = 0
        self.last_event = ""

    def on_order(self, status: str):
        self.total_orders += 1
        normalized = (status or "").upper()
        if normalized in {"FILLED", "SENT", "COMPLETE"}:
            self.filled_orders += 1
        elif normalized in {"REJECTED", "FAILED"}:
            self.rejected_orders += 1

    def on_event(self, event_type: str):
        self.last_event = event_type

    def snapshot(
        self,
        equity: float,
        cash: float,
        realized_pnl: float,
        open_positions: int,
        orders_today: int,
        recent_events: list[str],
    ) -> dict[str, float]:
        self.max_equity = max(self.max_equity, equity)
        self.min_equity = min(self.min_equity, equity)
        drawdown = 0.0
        if self.max_equity > 0:
            drawdown = ((equity - self.max_equity) / self.max_equity) * 100.0

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "equity": round(equity, 2),
            "cash": round(cash, 2),
            "realized_pnl": round(realized_pnl, 2),
            "open_positions": int(open_positions),
            "orders_today": int(orders_today),
            "total_orders": int(self.total_orders),
            "filled_orders": int(self.filled_orders),
            "rejected_orders": int(self.rejected_orders),
            "max_equity": round(self.max_equity, 2),
            "min_equity": round(self.min_equity if self.min_equity != float("inf") else equity, 2),
            "drawdown_pct": round(drawdown, 2),
            "last_event": self.last_event,
            "recent_events": recent_events[-10:],
        }

    def export(self, payload: dict[str, float]) -> bool:
        try:
            path = Path(self.output_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            return True
        except OSError:
            return False
