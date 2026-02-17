from __future__ import annotations

import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
HOOKS_DIR = REPO_ROOT / ".git" / "hooks"
PRE_COMMIT_HOOK = HOOKS_DIR / "pre-commit"

HOOK_CONTENT = """#!/usr/bin/env sh
python scripts/check_staged_secrets.py
if [ $? -ne 0 ]; then
  exit 1
fi
"""


def main() -> int:
    if not HOOKS_DIR.exists():
        print("Git hooks directory not found. Run this from a cloned git repository.")
        return 1

    HOOKS_DIR.mkdir(parents=True, exist_ok=True)
    PRE_COMMIT_HOOK.write_text(HOOK_CONTENT, encoding="utf-8")
    try:
        os.chmod(PRE_COMMIT_HOOK, 0o755)
    except OSError:
        pass

    print(f"Installed pre-commit hook: {PRE_COMMIT_HOOK}")
    print("This hook blocks commits that include likely secrets or credential files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
