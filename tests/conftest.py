from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture(autouse=True)
def isolated_cli_settings(monkeypatch, tmp_path):
    settings_file = tmp_path / "cli_settings.json"
    monkeypatch.setenv("CLI_SETTINGS_FILE", str(settings_file))
    yield
