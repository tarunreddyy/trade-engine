# Trade Engine CLI

Broker-agnostic command-line trading engine for orders, portfolio, strategy runtime, recommendations, and AI tooling.

## Install

### From source
```bash
pip install -e ".[groww]"
```

Broker extras:
- `.[groww]`
- `.[upstox]`
- `.[zerodha]`
- `.[all-brokers]`

### From PyPI
```bash
pip install "trade-engine-cli[groww]"
```

### Windows EXE
Download `trade-engine.exe` from GitHub Releases.

## Run
```bash
trade-engine
```
or
```bash
python main.py
```

## CLI Navigation

- All menus support:
  - numeric input (`1`, `2`, ...)
  - slash commands (`/1`, `/orders-management`, etc.)
- Type `/` in any menu to open the command palette.
- In chatbot and live runtime prompts, `/` shows available commands.

## Configure Everything in CLI

Main Menu -> `Settings`

You can configure:
- Active broker (`groww`, `upstox`, `zerodha`)
- Broker credentials/secrets
- LLM provider and API keys
- Pinecone API key and index
- Visualization defaults
- Live trading defaults and safety controls
- Order journal SQLite path
- Advanced key/value editor for any dotted key path

Settings persist to:
- `data/runtime/cli_settings.json` (default)
- Override path with env: `CLI_SETTINGS_FILE`

`.env` is optional fallback only.

## Configuration Reference

Settings are stored in `data/runtime/cli_settings.json` by default.  
Resolution order per key:
1. CLI settings JSON
2. Environment variable fallback
3. Built-in default

Supported keys (settable from CLI directly or via `Settings -> Advanced Key/Value`):

| Dotted Key | Env Fallback | Default |
|---|---|---|
| `broker.active` | `BROKER` | `groww` |
| `broker.groww.api_key` | `GROWW_API_KEY` | `""` |
| `broker.groww.api_secret` | `GROWW_API_SECRET` | `""` |
| `broker.groww.access_token` | `GROWW_ACCESS_TOKEN` | `""` |
| `broker.upstox.api_key` | `UPSTOX_API_KEY` | `""` |
| `broker.upstox.api_secret` | `UPSTOX_API_SECRET` | `""` |
| `broker.zerodha.api_key` | `ZERODHA_API_KEY` | `""` |
| `broker.zerodha.api_secret` | `ZERODHA_API_SECRET` | `""` |
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

## Real-Time Dashboard in CLI

Open:
- `Trading Strategies` -> `Live Trading Console`

Dashboard panels in terminal:
- Runtime controls (mode, buy/sell toggles, SL/TP, risk, kill switch, market-hours guard, orders/day)
- Account summary (cash, equity, realized PnL, open positions)
- Watchlist snapshot (price, change, signal, position, unrealized PnL)
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

Runtime artifacts:
- session state: `data/runtime/live_session_state.json`
- order journal: `data/runtime/order_journal.sqlite`
- metrics snapshot: `data/runtime/metrics_latest.json`

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
