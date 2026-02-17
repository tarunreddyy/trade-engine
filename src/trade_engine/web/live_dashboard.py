from __future__ import annotations

import json
import os
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
    :root {
      --bg: #08121f;
      --bg-soft: #0f1d2f;
      --card: #12243b;
      --card-alt: #152a45;
      --line: #28476d;
      --text: #dbeafe;
      --muted: #91a9c7;
      --buy: #22c55e;
      --sell: #f43f5e;
      --hold: #f59e0b;
      --accent: #38bdf8;
      --accent-2: #14b8a6;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI Variable Text", "Segoe UI", Arial, sans-serif;
      color: var(--text);
      background:
        radial-gradient(1200px 600px at -10% -20%, #1e3a8a40, transparent 60%),
        radial-gradient(1000px 500px at 110% 0%, #0f766e35, transparent 60%),
        linear-gradient(180deg, var(--bg), #070f1a 70%);
      min-height: 100vh;
    }
    .page { padding: 14px 16px 18px; }
    .sticky {
      position: sticky;
      top: 0;
      z-index: 20;
      backdrop-filter: blur(10px);
      background: #08121fcc;
      border-bottom: 1px solid var(--line);
      padding: 10px 16px;
      margin: -14px -16px 12px;
    }
    .title-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      flex-wrap: wrap;
    }
    h1 { margin: 0; font-size: 20px; letter-spacing: 0.3px; }
    .meta { color: var(--muted); font-size: 12px; }
    .chips { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
    .chip {
      background: var(--bg-soft);
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 12px;
      color: var(--text);
    }
    .chip b { color: #ffffff; }
    .layout {
      display: grid;
      grid-template-columns: 1.5fr 1fr;
      gap: 12px;
    }
    .stack { display: grid; gap: 12px; }
    .card {
      background: linear-gradient(180deg, var(--card), var(--card-alt));
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 10px 12px;
      box-shadow: inset 0 1px 0 #ffffff0d;
    }
    .card h2 {
      margin: 0 0 10px;
      font-size: 13px;
      color: #c6dbf5;
      letter-spacing: 0.25px;
      text-transform: uppercase;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12.5px;
    }
    th, td {
      border-bottom: 1px solid var(--line);
      padding: 6px;
      text-align: left;
      white-space: nowrap;
    }
    th {
      color: #93c5fd;
      font-weight: 600;
      background: #0b1a2b;
      position: sticky;
      top: 0;
    }
    tr:hover td { background: #1a3250; }
    .scroll { max-height: 300px; overflow: auto; border-radius: 8px; }
    .signal {
      font-size: 11px;
      padding: 2px 8px;
      border-radius: 999px;
      font-weight: 700;
      display: inline-block;
    }
    .buy { color: #04240f; background: var(--buy); }
    .sell { color: #fff1f2; background: var(--sell); }
    .hold { color: #2a1a03; background: var(--hold); }
    .up { color: var(--buy); font-weight: 600; }
    .down { color: var(--sell); font-weight: 600; }
    .muted { color: var(--muted); }
    @media (max-width: 1150px) { .layout { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <div class="page">
    <div class="sticky">
      <div class="title-row">
        <h1>Trade Engine Live Dashboard</h1>
        <div id="meta" class="meta"></div>
      </div>
      <div id="chips" class="chips"></div>
    </div>

    <div class="layout">
      <div class="stack">
        <div class="card">
          <h2>Strategy Watchlist (Latest Triggers On Top)</h2>
          <div id="watchlist" class="scroll"></div>
        </div>
        <div class="card">
          <h2>Signal Triggers (Capped + Deduped)</h2>
          <div id="triggers" class="scroll"></div>
        </div>
        <div class="card">
          <h2>Session Orders</h2>
          <div id="openOrders" class="scroll" style="margin-bottom: 10px;"></div>
          <div id="closedOrders" class="scroll"></div>
        </div>
      </div>

      <div class="stack">
        <div class="card">
          <h2>Live Positions</h2>
          <div id="positions" class="scroll"></div>
        </div>
        <div class="card">
          <h2>NSE Indexes</h2>
          <div id="indices" class="scroll"></div>
        </div>
        <div class="card">
          <h2>F&O Snapshot</h2>
          <div id="fno" class="scroll"></div>
        </div>
      </div>
    </div>
  </div>
  <script>
    function fmt(value, digits = 2) {
      if (value === null || value === undefined || value === "") return "-";
      const num = Number(value);
      if (Number.isNaN(num)) return String(value);
      return num.toFixed(digits);
    }
    function clsForPct(value) {
      const num = Number(value);
      if (Number.isNaN(num) || num === 0) return "muted";
      return num > 0 ? "up" : "down";
    }
    function signalBadge(signalText) {
      const text = String(signalText || "HOLD").toUpperCase();
      const cls = text === "BUY" ? "buy" : (text === "SELL" ? "sell" : "hold");
      return `<span class="signal ${cls}">${text}</span>`;
    }
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
        return `<tr>
          <td>${r.symbol ?? "-"}</td>
          <td>${fmt(r.price)}</td>
          <td class='${clsForPct(r.change_pct)}'>${fmt(r.change_pct)}%</td>
          <td>${signalBadge(r.signal_text)}</td>
          <td>${buy}</td>
          <td>${sell}</td>
        </tr>`;
      }).join("");
      return `<table>${head}${body}</table>`;
    }
    function renderPositions(rows) {
      if (!rows || rows.length === 0) return "<div class='muted'>No open positions</div>";
      const head = "<tr><th>Symbol</th><th>Side</th><th>Qty</th><th>Entry</th><th>LTP</th><th>uPnL</th></tr>";
      const body = rows.map(r => `
        <tr>
          <td>${r.symbol ?? "-"}</td>
          <td>${r.side ?? "-"}</td>
          <td>${r.quantity ?? "-"}</td>
          <td>${fmt(r.entry_price)}</td>
          <td>${fmt(r.market_price)}</td>
          <td class='${clsForPct(r.unrealized_pnl)}'>${fmt(r.unrealized_pnl)}</td>
        </tr>`).join("");
      return `<table>${head}${body}</table>`;
    }
    function renderTriggers(rows) {
      if (!rows || rows.length === 0) return "<div class='muted'>No BUY/SELL triggers yet</div>";
      const head = "<tr><th>Time</th><th>Symbol</th><th>Signal</th><th>Price</th><th>Action</th></tr>";
      const body = rows.map(r => `
        <tr>
          <td>${r.timestamp ?? "-"}</td>
          <td>${r.symbol ?? "-"}</td>
          <td>${signalBadge(r.signal_text)}</td>
          <td>${fmt(r.price)}</td>
          <td>${r.action ?? "-"}</td>
        </tr>`).join("");
      return `<table>${head}${body}</table>`;
    }
    function renderIndex(rows) {
      if (!rows || rows.length === 0) return "<div class='muted'>No index data</div>";
      const head = "<tr><th>Name</th><th>Symbol</th><th>LTP</th><th>Chg%</th></tr>";
      const body = rows.map(r => `
        <tr>
          <td>${r.name ?? "-"}</td>
          <td>${r.symbol ?? "-"}</td>
          <td>${fmt(r.ltp)}</td>
          <td class='${clsForPct(r.change_pct)}'>${fmt(r.change_pct)}%</td>
        </tr>`).join("");
      return `<table>${head}${body}</table>`;
    }
    function renderFno(rows) {
      if (!rows || rows.length === 0) return "<div class='muted'>No F&O data</div>";
      const head = "<tr><th>Symbol</th><th>Segment</th><th>LTP</th><th>Chg%</th></tr>";
      const body = rows.map(r => `
        <tr>
          <td>${r.symbol ?? "-"}</td>
          <td>${r.segment ?? "-"}</td>
          <td>${fmt(r.ltp)}</td>
          <td class='${clsForPct(r.change_pct)}'>${fmt(r.change_pct)}%</td>
        </tr>`).join("");
      return `<table>${head}${body}</table>`;
    }
    function renderOrderTable(rows) {
      if (!rows || rows.length === 0) return "<div class='muted'>No rows</div>";
      const head = "<tr><th>Time</th><th>Symbol</th><th>Side</th><th>Qty</th><th>Price</th><th>Status</th></tr>";
      const body = rows.map(r => `
        <tr>
          <td>${r.created_at ?? "-"}</td>
          <td>${r.symbol ?? "-"}</td>
          <td>${r.side ?? "-"}</td>
          <td>${r.quantity ?? "-"}</td>
          <td>${fmt(r.price)}</td>
          <td>${r.status ?? "-"}</td>
        </tr>`).join("");
      return `<table>${head}${body}</table>`;
    }
    async function refresh() {
      const response = await fetch("/api/state");
      const data = await response.json();
      document.getElementById("meta").innerText = `${data.strategy_name || "-"} | mode=${String(data.mode || "-").toUpperCase()} | updated=${data.updated_at || "-"}`;
      document.getElementById("chips").innerHTML = `
        <div class="chip">Cash: <b>${fmt(data.cash)}</b></div>
        <div class="chip">Equity: <b>${fmt(data.equity)}</b></div>
        <div class="chip">Realized PnL: <b>${fmt(data.realized_pnl)}</b></div>
        <div class="chip">Positions: <b>${(data.positions || []).length}</b></div>
        <div class="chip">Triggers: <b>${(data.signal_triggers || []).length}</b></div>
      `;
      document.getElementById("watchlist").innerHTML = renderWatchlist(data.watchlist || []);
      document.getElementById("positions").innerHTML = renderPositions(data.positions || []);
      document.getElementById("openOrders").innerHTML = renderOrderTable(data.open_orders || []);
      document.getElementById("closedOrders").innerHTML = renderOrderTable(data.closed_orders || []);
      document.getElementById("triggers").innerHTML = renderTriggers(data.signal_triggers || []);
      document.getElementById("indices").innerHTML = renderIndex(data.indices || []);
      document.getElementById("fno").innerHTML = renderFno(data.fno || []);
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
            if open_browser:
                try:
                    if os.name == "nt":
                        os.startfile(self.url)  # type: ignore[attr-defined]
                    else:
                        webbrowser.open(self.url, new=2)
                except Exception:
                    pass
            return self.url
        handler = type("DashboardHandler", (_DashboardRequestHandler,), {})
        handler.state_file = self.state_file
        handler.control_file = self.control_file
        self._httpd = ThreadingHTTPServer((self.host, self.port), handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        if open_browser:
            try:
                if os.name == "nt":
                    os.startfile(self.url)  # type: ignore[attr-defined]
                else:
                    webbrowser.open(self.url, new=2)
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
