import json
import os
import tempfile
from datetime import datetime
from typing import Any


class SessionStateStore:
    """JSON-based persistence for live trading console state."""

    def __init__(self, state_file: str):
        self.state_file = state_file

    def load_state(self) -> dict[str, Any] | None:
        if not os.path.exists(self.state_file):
            return None
        try:
            with open(self.state_file, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            return None

    def save_state(self, state: dict[str, Any]) -> bool:
        try:
            state = dict(state)
            state["saved_at"] = datetime.utcnow().isoformat()
            directory = os.path.dirname(self.state_file) or "."
            os.makedirs(directory, exist_ok=True)

            fd, temp_path = tempfile.mkstemp(prefix="session_", suffix=".json", dir=directory)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(state, handle, indent=2)
                os.replace(temp_path, self.state_file)
            finally:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except OSError:
                        pass
            return True
        except Exception:
            return False

    def clear_state(self) -> bool:
        try:
            if os.path.exists(self.state_file):
                os.remove(self.state_file)
            return True
        except Exception:
            return False


