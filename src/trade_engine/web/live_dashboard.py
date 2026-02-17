from __future__ import annotations

import json
import threading
import webbrowser
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from trade_engine.core.market_data_service import MarketDataService


def _read_json(path: str, default: Any) -> Any:
    target = Path(path)
    if not target.exists():
        return default
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: str, payload: Any) -> bool:
    target = Path(path)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return True
    except OSError:
        return False


def read_dashboard_controls(control_file: str) -> dict[str, Any]:
    payload = _read_json(control_file, {})
    if not isinstance(payload, dict):
        return {}
    return payload


def write_dashboard_state(state_file: str, payload: dict[str, Any]) -> bool:
    merged = dict(payload)
    merged["updated_at"] = datetime.utcnow().isoformat()
    return _write_json(state_file, merged)


def _fallback_payload(symbols: list[str] | None = None) -> dict[str, Any]:
    service = MarketDataService()
    watchlist_symbols = symbols or ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS"]
    quotes = service.get_batch_snapshot(watchlist_symbols, exchange="NSE", segment="CASH")
    watchlist = [
        {
            "symbol": row.get("symbol"),
            "price": row.get("ltp"),
            "change_pct": row.get("change_pct"),
            "signal": 0,
            "signal_text": "HOLD",
            "buy_enabled": True,
            "sell_enabled": True,
        }
        for row in quotes
    ]
    return {
        "strategy_name": "Not running",
        "mode": "paper",
        "watchlist": watchlist,
        "indices": service.get_indices_snapshot(),
        "fno": service.get_fno_snapshot(),
        "positions": [],
        "open_orders": [],
        "closed_orders": [],
        "signal_triggers": [],
        "message": "Live strategy session not running. Showing market data fallback.",
        "updated_at": datetime.utcnow().isoformat(),
    }


def _dashboard_html() -> str:
    return """<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Trade Engine Live Dashboard</title>
  <style>
    body { font-family: Segoe UI, Arial, sans-serif; margin: 16px; background: #0f172a; color: #e2e8f0; }
    h1,h2 { margin: 8px 0; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 12px; }
    .card { background: #111827; border: 1px solid #1f2937; border-radius: 8px; padding: 12px; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { border-bottom: 1px solid #1f2937; padding: 6px; text-align: left; }
    .ok { color: #22c55e; } .bad { color: #ef4444; } .muted { color: #94a3b8; }
    button { background: #2563eb; color: white; border: 0; border-radius: 6px; padding: 5px 8px; cursor: pointer; }
    input, select { background: #0b1220; color: #e2e8f0; border: 1px solid #334155; border-radius: 6px; padding: 6px; }
  </style>
</head>
<body>
  <h1>Trade Engine Live Dashboard</h1>
  <div id="meta" class="muted"></div>
  <div class="grid">
    <div class="card"><h2>Signal Triggers (Latest First)</h2><div id="triggers"></div></div>
    <div class="card"><h2>Live Positions</h2><div id="positions"></div></div>
    <div class="card"><h2>Open Orders (Session)</h2><div id="openOrders"></div></div>
    <div class="card"><h2>Closed Orders (Session)</h2><div id="closedOrders"></div></div>
  </div>
  <div class="grid" style="margin-top: 12px;">
    <div class="card"><h2>Strategy Watchlist</h2><div id="watchlist"></div></div>
    <div class="card"><h2>NSE Indexes</h2><div id="indices"></div></div>
    <div class="card"><h2>F&O Watch</h2><div id="fno"></div></div>
  </div>
  <script>
    function renderTable(rows, cols) {
      if (!rows || rows.length === 0) return "<div class='muted'>No data</div>";
      const head = "<tr>" + cols.map(c => `<th>${c}</th>`).join("") + "</tr>";
      const body = rows.map(r => "<tr>" + cols.map(c => `<td>${r[c] ?? "-"}</td>`).join("") + "</tr>").join("");
      return `<table>${head}${body}</table>`;
    }
    async function sendControl(symbol, side, enabled) {
      await fetch("/api/control", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({symbol, side, enabled}),
      });
    }
    function renderWatchlist(rows) {
      if (!rows || rows.length === 0) return "<div class='muted'>No watchlist data</div>";
      const head = "<tr><th>Symbol</th><th>LTP</th><th>Chg%</th><th>Signal</th><th>Buy</th><th>Sell</th></tr>";
      const body = rows.map(r => {
        const buy = `<input type='checkbox' ${r.buy_enabled ? "checked":""} onchange='sendControl("${r.symbol}","buy",this.checked)' />`;
        const sell = `<input type='checkbox' ${r.sell_enabled ? "checked":""} onchange='sendControl("${r.symbol}","sell",this.checked)' />`;
        return `<tr><td>${r.symbol}</td><td>${r.price ?? "-"}</td><td>${r.change_pct ?? "-"}</td><td>${r.signal_text ?? "-"}</td><td>${buy}</td><td>${sell}</td></tr>`;
      }).join("");
      return `<table>${head}${body}</table>`;
    }
    async function refresh() {
      const response = await fetch("/api/state");
      const data = await response.json();
      document.getElementById("meta").innerText = `${data.strategy_name || "-"} | mode=${data.mode || "-"} | updated=${data.updated_at || "-"}`;
      document.getElementById("watchlist").innerHTML = renderWatchlist(data.watchlist || []);
      document.getElementById("positions").innerHTML = renderTable(data.positions || [], ["symbol","side","quantity","entry_price","market_price","unrealized_pnl"]);
      document.getElementById("openOrders").innerHTML = renderTable(data.open_orders || [], ["created_at","symbol","side","quantity","price","status"]);
      document.getElementById("closedOrders").innerHTML = renderTable(data.closed_orders || [], ["created_at","symbol","side","quantity","price","status"]);
      document.getElementById("triggers").innerHTML = renderTable(data.signal_triggers || [], ["timestamp","symbol","signal_text","price","action"]);
      document.getElementById("indices").innerHTML = renderTable(data.indices || [], ["name","symbol","ltp","change_pct"]);
      document.getElementById("fno").innerHTML = renderTable(data.fno || [], ["symbol","ltp","change_pct"]);
    }
    refresh();
    setInterval(refresh, 2500);
  </script>
</body>
</html>
"""


class _DashboardRequestHandler(BaseHTTPRequestHandler):
    state_file: str = "data/runtime/live_dashboard.json"
    control_file: str = "data/runtime/live_dashboard_controls.json"

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            body = _dashboard_html().encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/api/state":
            payload = _read_json(self.state_file, None)
            if not isinstance(payload, dict):
                payload = _fallback_payload()
            elif str(payload.get("strategy_name", "")).lower().startswith("no live strategy"):
                symbols = [
                    str(row.get("symbol", "")).strip().upper()
                    for row in payload.get("watchlist", [])
                    if isinstance(row, dict) and str(row.get("symbol", "")).strip()
                ]
                payload = _fallback_payload(symbols=symbols)
            self._send_json(payload)
            return
        self._send_json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/control":
            self._send_json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)
            return

        content_length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json({"error": "invalid_json"}, status=HTTPStatus.BAD_REQUEST)
            return

        controls = read_dashboard_controls(self.control_file)
        symbol = str(payload.get("symbol", "")).strip().upper()
        side = str(payload.get("side", "")).strip().lower()
        enabled = bool(payload.get("enabled", True))
        if symbol and side in {"buy", "sell"}:
            symbol_controls = controls.setdefault("symbol_controls", {})
            per_symbol = symbol_controls.setdefault(symbol, {"buy": True, "sell": True})
            per_symbol[side] = enabled
            controls["updated_at"] = datetime.utcnow().isoformat()
            _write_json(self.control_file, controls)
            self._send_json({"ok": True, "symbol": symbol, "side": side, "enabled": enabled})
            return

        self._send_json({"error": "invalid_payload"}, status=HTTPStatus.BAD_REQUEST)

    def log_message(self, format: str, *args):
        return


class LiveDashboardServer:
    def __init__(self, host: str, port: int, state_file: str, control_file: str):
        self.host = host
        self.port = int(port)
        self.state_file = state_file
        self.control_file = control_file
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def start(self, open_browser: bool = False) -> str:
        if self._httpd:
            return self.url
        handler = type("DashboardHandler", (_DashboardRequestHandler,), {})
        handler.state_file = self.state_file
        handler.control_file = self.control_file
        self._httpd = ThreadingHTTPServer((self.host, self.port), handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        if open_browser:
            try:
                webbrowser.open(self.url)
            except Exception:
                pass
        return self.url

    def stop(self):
        if not self._httpd:
            return
        self._httpd.shutdown()
        self._httpd.server_close()
        self._httpd = None
        self._thread = None
