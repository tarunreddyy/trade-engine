import importlib.util
import subprocess
import sys

from trade_engine.config.broker_config import SUPPORTED_BROKERS

BROKER_SDKS: dict[str, dict[str, list[str]]] = {
    "none": {
        "packages": [],
        "imports": [],
    },
    "groww": {
        "packages": ["growwapi", "pyotp"],
        "imports": ["growwapi", "pyotp"],
    },
    "upstox": {
        "packages": [],
        "imports": [],
    },
    "zerodha": {
        "packages": [],
        "imports": [],
    },
}


def _normalize_broker(broker_name: str) -> str:
    normalized = str(broker_name or "").strip().lower()
    if normalized not in SUPPORTED_BROKERS:
        supported = ", ".join(SUPPORTED_BROKERS)
        raise ValueError(f"Unsupported broker '{broker_name}'. Supported: {supported}")
    return normalized


def get_broker_sdk_status(broker_name: str) -> dict[str, object]:
    broker = _normalize_broker(broker_name)
    definition = BROKER_SDKS[broker]
    missing_imports = [
        module_name
        for module_name in definition["imports"]
        if importlib.util.find_spec(module_name) is None
    ]
    return {
        "broker": broker,
        "installed": len(missing_imports) == 0,
        "missing_imports": missing_imports,
        "required_packages": definition["packages"],
    }


def list_broker_sdk_status() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for broker in SUPPORTED_BROKERS:
        status = get_broker_sdk_status(broker)
        rows.append(
            {
                "broker": status["broker"],
                "installed": "yes" if status["installed"] else "no",
                "missing_imports": ", ".join(status["missing_imports"]) if status["missing_imports"] else "-",
                "packages": ", ".join(status["required_packages"]) if status["required_packages"] else "-",
            }
        )
    return rows


def install_broker_sdk(broker_name: str, upgrade: bool = False) -> tuple[bool, str]:
    broker = _normalize_broker(broker_name)
    definition = BROKER_SDKS[broker]
    if not definition["packages"]:
        return True, "No SDK required for broker-free mode."
    command = [sys.executable, "-m", "pip", "install"]
    if upgrade:
        command.append("--upgrade")
    command.extend(definition["packages"])

    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception as error:
        return False, f"Failed to invoke pip for {broker}: {error}"

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        stdout = (completed.stdout or "").strip()
        detail = stderr or stdout or "unknown pip error"
        return False, f"SDK install failed for {broker}: {detail}"

    status = get_broker_sdk_status(broker)
    if not status["installed"]:
        missing = ", ".join(status["missing_imports"])
        return False, f"Install completed but imports still missing for {broker}: {missing}"
    return True, f"{broker.title()} SDK installed and ready."
