# Trade Engine CLI

Broker-agnostic command-line trading engine for order management, portfolio workflows, strategy execution, recommendations, and AI-assisted analysis.

## Install Options

### 1) Install from source (recommended for contributors)
```bash
pip install -e ".[groww]"
```

Use one of these extras based on your broker:
- `.[groww]`
- `.[upstox]`
- `.[zerodha]`
- `.[all-brokers]`

### 2) Install from PyPI (for users)
```bash
pip install "trade-engine-cli[groww]"
```

### 3) Windows executable (no Python required on user machine)
Download `trade-engine.exe` from GitHub Release artifacts.

## Quick Start
1. Run:
   ```bash
   trade-engine
   ```
2. Open `Settings` in the main menu and configure:
   - active broker
   - broker credentials
   - LLM provider/API keys
   - Pinecone settings
   - live trading defaults (SL/TP/risk/max position)
   - safety controls (kill switch, market-hours guard, max orders/day)
3. Optional: keep `.env` as fallback only (if CLI settings file is missing).
4. You can still run with:
   ```bash
   python main.py
   ```

## Build Commands

### Build wheel + sdist
```bash
python -m pip install --upgrade pip
pip install ".[build]"
python -m build
```

### Build Windows EXE (PyInstaller)
```bash
python -m pip install --upgrade pip
pip install ".[build,groww]"
pyinstaller --clean trade_engine.spec
```

## Release Automation
- `CI` workflow: builds package and runs compile smoke check.
- `Release` workflow:
  - builds wheel/sdist and publishes to PyPI (Trusted Publishing)
  - builds Windows `trade-engine.exe` and uploads release artifact
- Full operator steps are in `RELEASE.md`.

## Project Structure
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
|- main.py
|- pyproject.toml
|- trade_engine.spec
'- requirements.txt
```
