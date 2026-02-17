from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_FILE_NAMES = {".env.template"}
ASSIGNMENT_SCAN_SUFFIXES = {
    ".env",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".txt",
}
BLOCKED_PATH_PATTERNS = (
    re.compile(r"(^|/)\.env($|[.].+)", re.IGNORECASE),
    re.compile(r"(^|/)cli_settings([._-].*)?[.]json$", re.IGNORECASE),
    re.compile(r"(^|/).*(credential|secret).*[.](json|ya?ml|toml|ini|env|txt)$", re.IGNORECASE),
)

SUSPECT_ASSIGNMENT = re.compile(
    r"""
    \b(
        api[_-]?key|
        api[_-]?secret|
        access[_-]?token|
        request[_-]?token|
        auth[_-]?code|
        client[_-]?secret|
        private[_-]?key|
        password|
        bearer
    )\b
    \s*[:=]\s*
    ["']?([^\s"',}]{8,})["']?
    """,
    flags=re.IGNORECASE | re.VERBOSE,
)

GENERIC_TOKEN = re.compile(
    r"""
    \b(
        sk-[a-z0-9]{20,}|
        ghp_[a-z0-9]{20,}|
        github_pat_[a-z0-9_]{20,}|
        xox[baprs]-[a-z0-9-]{10,}|
        ya29\.[a-z0-9._-]{20,}
    )\b
    """,
    flags=re.IGNORECASE | re.VERBOSE,
)


def _run_git(args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return ""
    return (completed.stdout or "").strip()


def _git_tracked_files() -> list[Path]:
    output = _run_git(["ls-files"])
    files: list[Path] = []
    for line in output.splitlines():
        line = line.strip()
        if line:
            files.append(Path(line))
    return files


def _git_staged_files() -> list[Path]:
    output = _run_git(["diff", "--cached", "--name-only", "--diff-filter=ACMRTUXB"])
    files: list[Path] = []
    for line in output.splitlines():
        line = line.strip()
        if line:
            files.append(Path(line))
    return files


def _is_likely_binary(blob: bytes) -> bool:
    return b"\x00" in blob


def _is_suspicious_value(value: str) -> bool:
    text = value.strip().strip("'\"")
    if len(text) < 8:
        return False

    lowered = text.lower()
    if lowered in {"null", "none", "false", "true", "changeme", "example", "placeholder"}:
        return False
    if lowered.startswith("your_") and lowered.endswith("_here"):
        return False
    if text.startswith("<") and text.endswith(">"):
        return False
    if set(text) == {"*"}:
        return False
    if re.fullmatch(r"[A-Z0-9_]+", text):
        # Looks like env-var name, not real secret.
        return False
    return True


def _scan_text(path: Path, content: str) -> list[str]:
    findings: list[str] = []
    normalized = path.as_posix()
    file_name = path.name.lower()
    suffix = path.suffix.lower()
    if file_name in ALLOWED_FILE_NAMES:
        return findings

    for pattern in BLOCKED_PATH_PATTERNS:
        if pattern.search(normalized):
            findings.append(f"{normalized}: blocked secret file path pattern.")
            break

    if suffix in ASSIGNMENT_SCAN_SUFFIXES or file_name.startswith(".env"):
        for match in SUSPECT_ASSIGNMENT.finditer(content):
            key_name = match.group(1)
            value = match.group(2)
            if _is_suspicious_value(value):
                findings.append(f"{normalized}: suspicious `{key_name}` assignment.")
                break

    if GENERIC_TOKEN.search(content):
        findings.append(f"{normalized}: token-like literal detected.")

    return findings


def _scan_paths(paths: list[Path]) -> list[str]:
    findings: list[str] = []
    for rel_path in paths:
        abs_path = REPO_ROOT / rel_path
        if not abs_path.exists() or not abs_path.is_file():
            continue
        try:
            blob = abs_path.read_bytes()
        except OSError:
            continue
        if _is_likely_binary(blob):
            continue
        try:
            text = blob.decode("utf-8")
        except UnicodeDecodeError:
            text = blob.decode("utf-8", errors="ignore")
        findings.extend(_scan_text(rel_path, text))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Block accidental secret commits.")
    parser.add_argument("--all", action="store_true", help="Scan all tracked files instead of staged files.")
    args = parser.parse_args()

    paths = _git_tracked_files() if args.all else _git_staged_files()
    if not paths:
        return 0

    findings = _scan_paths(paths)
    if not findings:
        return 0

    print("\n[trade-engine] Secret guard blocked this commit.\n")
    for finding in findings:
        print(f"- {finding}")
    print("\nFix:")
    print("- Remove secrets from staged files.")
    print("- Keep credentials in CLI settings file (outside repo by default).")
    print("- Use `.env.template` for examples only.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
