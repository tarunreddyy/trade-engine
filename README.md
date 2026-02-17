# Trade Engine CLI

Broker-agnostic command-line trading engine for orders, portfolio, strategy runtime, recommendations, and AI tooling.

## Install

### One-line install (recommended)
```bash
pipx install trade-engine-cli
```

If installing directly from this repository:
```bash
pipx install "git+https://github.com/tarunreddyy/trade-engine.git"
```

Run:
```bash
trade_engine
```

Also available:
```bash
trade-engine
```

### From source
```bash
pip install -e .
```

Optional broker extras:
- `.[groww]`
- `.[upstox]`
- `.[zerodha]`
- `.[all-brokers]`

Note: Upstox and Zerodha adapters work via REST without SDK installation. Groww still requires its SDK.

### From PyPI
```bash
pip install trade-engine-cli
```

### Windows EXE
Download `trade-engine.exe` from GitHub Releases.

## Run
```bash
trade_engine
```
or
```bash
trade-engine
```
or
```bash
python main.py
```

First-time users:
- Open `Quick Setup` from Main Menu
- Select broker
- Enter broker credentials

Default beginner flow:
- `Start Live Scanner` from main menu
- default strategy is `HLC3 Pivot Breakout`
- scans full configured universe (EQ + F&O watch) and ranks latest BUY/SELL triggers
- no risk/SL/TP prompts unless you choose `Start Auto Trader`

Simplified main menu:
- `Start Live Scanner`
- `Dashboard`
- `Orders`
- `Portfolio`
- `Settings`
- `More Tools`

## CLI Navigation

- All menus support:
  - numeric input (`1`, `2`, ...)
  - slash commands (`/1`, `/orders-management`, etc.)
- Menus are hidden by default for a cleaner terminal.
- Type `/` in any menu to open the command palette dropdown instantly and use arrow keys to select.
- On Windows menus, `Left Arrow` goes back when a Back option exists, and `Right Arrow` opens palette.
- In chatbot and live runtime prompts, `/` shows available commands.
- Slash matching supports direct command, numeric, and unique prefix resolution.

## Configure Everything in CLI

Main Menu -> `Settings`

You can configure:
- Active broker (`none`, `groww`, `upstox`, `zerodha`)
- Broker SDK install/load (`Settings` -> `Broker SDKs`, Groww only required)
- Broker credentials/secrets
- LLM provider and API keys
- Pinecone API key and index
- Visualization defaults
- Live trading defaults and safety controls
- Order journal SQLite path
- Advanced key/value editor for any dotted key path

Settings persist to:
- Windows: `%APPDATA%\\trade-engine\\cli_settings.json` (default)
- macOS/Linux: `~/.trade_engine/cli_settings.json` (default)
- Override path with env: `CLI_SETTINGS_FILE`

`.env` is optional fallback only.

## Configuration Reference

Settings are stored in a user-home/AppData path by default (outside your git repo).  
Resolution order per key:
1. CLI settings JSON
2. Environment variable fallback
3. Built-in default

## Secret Safety

- Local credential files are git-ignored by default.
- A secret-guard script is included to block accidental commits of tokens/secrets.

Install the git hook once per clone:
```bash
python scripts/install_git_hooks.py
```

Supported keys (settable from CLI directly or via `Settings -> Advanced Key/Value`):

| Dotted Key | Env Fallback | Default |
|---|---|---|
| `broker.active` | `BROKER` | `none` |
| `broker.groww.api_key` | `GROWW_API_KEY` | `""` |
| `broker.groww.api_secret` | `GROWW_API_SECRET` | `""` |
| `broker.groww.access_token` | `GROWW_ACCESS_TOKEN` | `""` |
| `broker.upstox.api_key` | `UPSTOX_API_KEY` | `""` |
| `broker.upstox.api_secret` | `UPSTOX_API_SECRET` | `""` |
| `broker.upstox.access_token` | `UPSTOX_ACCESS_TOKEN` | `""` |
| `broker.upstox.redirect_uri` | `UPSTOX_REDIRECT_URI` | `""` |
| `broker.upstox.auth_code` | `UPSTOX_AUTH_CODE` | `""` |
| `broker.zerodha.api_key` | `ZERODHA_API_KEY` | `""` |
| `broker.zerodha.api_secret` | `ZERODHA_API_SECRET` | `""` |
| `broker.zerodha.access_token` | `ZERODHA_ACCESS_TOKEN` | `""` |
| `broker.zerodha.request_token` | `ZERODHA_REQUEST_TOKEN` | `""` |
| `llm.provider` | `LLM_PROVIDER` | `openai` |
| `llm.openai_api_key` | `OPENAI_API_KEY` | `""` |
| `llm.claude_api_key` | `CLAUDE_API_KEY` | `""` |
| `llm.gemini_api_key` | `GEMINI_API_KEY` | `""` |
| `pinecone.api_key` | `PINECONE_API_KEY` | `""` |
| `pinecone.index_name_eq` | `PINECONE_INDEX_NAME_EQ` | `groww-instruments-eq` |
| `visualization.default_period` | `VIS_DEFAULT_PERIOD` | `1mo` |
| `visualization.default_interval` | `VIS_DEFAULT_INTERVAL` | `1d` |
| `visualization.default_chart_type` | `VIS_DEFAULT_CHART_TYPE` | `candlestick` |
| `trading.live_default_mode` | `LIVE_DEFAULT_MODE` | `paper` |
| `trading.live_default_refresh_seconds` | `LIVE_DEFAULT_REFRESH_SECONDS` | `15` |
| `trading.live_default_stop_loss_pct` | `LIVE_DEFAULT_STOP_LOSS_PCT` | `2.0` |
| `trading.live_default_take_profit_pct` | `LIVE_DEFAULT_TAKE_PROFIT_PCT` | `4.0` |
| `trading.live_default_risk_per_trade_pct` | `LIVE_DEFAULT_RISK_PER_TRADE_PCT` | `1.0` |
| `trading.live_default_max_position_pct` | `LIVE_DEFAULT_MAX_POSITION_PCT` | `10.0` |
| `trading.live_session_state_file` | `LIVE_SESSION_STATE_FILE` | `data/runtime/live_session_state.json` |
| `trading.live_auto_resume_session` | `LIVE_AUTO_RESUME_SESSION` | `true` |
| `trading.kill_switch_enabled` | `TRADING_KILL_SWITCH_ENABLED` | `false` |
| `trading.live_market_hours_only` | `LIVE_MARKET_HOURS_ONLY` | `true` |
| `trading.live_max_orders_per_day` | `LIVE_MAX_ORDERS_PER_DAY` | `40` |
| `trading.order_journal_file` | `ORDER_JOURNAL_FILE` | `data/runtime/order_journal.sqlite` |
| `trading.live_dashboard_state_file` | `LIVE_DASHBOARD_STATE_FILE` | `data/runtime/live_dashboard.json` |
| `trading.live_dashboard_control_file` | `LIVE_DASHBOARD_CONTROL_FILE` | `data/runtime/live_dashboard_controls.json` |
| `trading.live_dashboard_port` | `LIVE_DASHBOARD_PORT` | `8765` |

## Live Dashboard (Web + CLI)

Open:
- `Start Live Scanner` (beginner mode, signal-only)
- `More Tools` -> `Strategies (Advanced)` -> `Start Auto Trader` (order execution mode)

Web dashboard:
- URL: `http://127.0.0.1:8765` (port configurable in CLI settings)
- Shows strategy watchlist, live positions, session open/closed orders, signal triggers (latest first), NSE indexes, and F&O snapshot
- Per-symbol trigger controls:
  - toggle BUY and SELL for each watchlist symbol directly in the dashboard
  - latest trigger events stay at the top

CLI live screen:
- Runtime controls (mode, buy/sell toggles, SL/TP, risk, kill switch, market-hours guard, orders/day)
- Account summary (cash, equity, realized PnL, open positions)
- Watchlist snapshot (price, change, signal, per-symbol BUY/SELL enabled flags, position, unrealized PnL)
- Recent events log
- Equity trend sparkline

Live runtime commands:
- `/` (show command list)
- `/buy on|off`, `/sell on|off`
- `/sl <pct>`, `/tp <pct>`, `/risk <pct>`, `/maxpos <pct>`
- `/kill on|off`, `/hours on|off`, `/maxorders <n>`
- `/mode paper|live`
- `/add <SYM>`, `/remove <SYM>`
- `/clearstate`, `/help`, `/quit`
- Short aliases: `/b`, `/s`, `/r`, `/m`, `/q`, `/h`, `/ls`, `/pt`, `/mp`, `/ko`, `/mh`, `/mo`, `/a`, `/rm`, `/cs`

The CLI live view is static and top-anchored (Rich `Live` full-screen) so it does not keep appending new lines.

Main menu session header:
- top panel shows current holdings symbols (from session state), open trades, closed trades, and total orders for the current CLI session.

Broker-free mode:
- set broker to `none` in `Quick Setup` or `Settings`
- market data remains available through Yahoo Finance (`yfinance`) for quotes/search/live dashboard snapshots without any broker SDK.

Runtime artifacts:
- session state: `data/runtime/live_session_state.json`
- order journal: `data/runtime/order_journal.sqlite`
- metrics snapshot: `data/runtime/metrics_latest.json`
- dashboard state: `data/runtime/live_dashboard.json`
- dashboard controls: `data/runtime/live_dashboard_controls.json`

## Build

### Wheel + sdist
```bash
python -m pip install --upgrade pip
pip install ".[build]"
python -m build
```

### Windows EXE
```bash
python -m pip install --upgrade pip
pip install ".[build,all-brokers]"
pyinstaller --clean trade_engine.spec
```

Or use scripts:
- `build_scripts/build_package.bat`
- `build_scripts/build_package.sh`
- `build_scripts/build_exe.bat`
- `build_scripts/build_exe.sh`

## CI / Release

- CI: lint + tests + compile + package build
- Release workflow:
  - build wheel/sdist
  - publish to PyPI (trusted publishing)
  - build and upload Windows EXE artifact

See `RELEASE.md` for release playbook.

## Project Layout

```text
trade-engine/
|- src/trade_engine/
|  |- brokers/
|  |- cli/
|  |- config/
|  |- core/
|  |- engine/
|  |- strategies/
|  |- web/
|  |- exception/
|  '- logging/
|- data/
|  |- market/
|  |- artifacts/
|  '- runtime/
|- research/notebooks/
|- build_scripts/
|- .github/workflows/
|- pyproject.toml
|- trade_engine.spec
'- main.py
```
