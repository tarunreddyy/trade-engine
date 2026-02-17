import shutil
import sys
from pathlib import Path
from uuid import uuid4

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

TMP_ROOT = ROOT / ".tmp" / "pytest"
TMP_ROOT.mkdir(parents=True, exist_ok=True)


@pytest.fixture(autouse=True)
def isolated_cli_settings(monkeypatch):
    runtime_root = TMP_ROOT / "settings"
    runtime_root.mkdir(parents=True, exist_ok=True)
    temp_dir = runtime_root / f"trade_engine_{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    settings_file = temp_dir / "cli_settings.json"
    monkeypatch.setenv("CLI_SETTINGS_FILE", str(settings_file))
    try:
        yield
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
