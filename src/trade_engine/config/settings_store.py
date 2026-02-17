import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

load_dotenv()


SETTINGS_FILE_ENV = "CLI_SETTINGS_FILE"
DEFAULT_SETTINGS_FILE = "data/runtime/cli_settings.json"

ENV_MAPPING: Dict[str, str] = {
    "broker.active": "BROKER",
    "broker.groww.api_key": "GROWW_API_KEY",
    "broker.groww.api_secret": "GROWW_API_SECRET",
    "broker.groww.access_token": "GROWW_ACCESS_TOKEN",
    "broker.upstox.api_key": "UPSTOX_API_KEY",
    "broker.upstox.api_secret": "UPSTOX_API_SECRET",
    "broker.zerodha.api_key": "ZERODHA_API_KEY",
    "broker.zerodha.api_secret": "ZERODHA_API_SECRET",
    "llm.provider": "LLM_PROVIDER",
    "llm.openai_api_key": "OPENAI_API_KEY",
    "llm.claude_api_key": "CLAUDE_API_KEY",
    "llm.gemini_api_key": "GEMINI_API_KEY",
    "pinecone.api_key": "PINECONE_API_KEY",
    "pinecone.index_name_eq": "PINECONE_INDEX_NAME_EQ",
    "trading.live_default_mode": "LIVE_DEFAULT_MODE",
    "trading.live_default_refresh_seconds": "LIVE_DEFAULT_REFRESH_SECONDS",
    "trading.live_default_stop_loss_pct": "LIVE_DEFAULT_STOP_LOSS_PCT",
    "trading.live_default_take_profit_pct": "LIVE_DEFAULT_TAKE_PROFIT_PCT",
    "trading.live_default_risk_per_trade_pct": "LIVE_DEFAULT_RISK_PER_TRADE_PCT",
    "trading.live_default_max_position_pct": "LIVE_DEFAULT_MAX_POSITION_PCT",
    "trading.live_session_state_file": "LIVE_SESSION_STATE_FILE",
    "trading.live_auto_resume_session": "LIVE_AUTO_RESUME_SESSION",
    "trading.kill_switch_enabled": "TRADING_KILL_SWITCH_ENABLED",
    "trading.live_market_hours_only": "LIVE_MARKET_HOURS_ONLY",
    "trading.live_max_orders_per_day": "LIVE_MAX_ORDERS_PER_DAY",
    "trading.order_journal_file": "ORDER_JOURNAL_FILE",
    "visualization.default_period": "VIS_DEFAULT_PERIOD",
    "visualization.default_interval": "VIS_DEFAULT_INTERVAL",
    "visualization.default_chart_type": "VIS_DEFAULT_CHART_TYPE",
}

DEFAULT_SETTINGS: Dict[str, Any] = {
    "broker": {
        "active": "groww",
        "groww": {
            "api_key": "",
            "api_secret": "",
            "access_token": "",
        },
        "upstox": {
            "api_key": "",
            "api_secret": "",
        },
        "zerodha": {
            "api_key": "",
            "api_secret": "",
        },
    },
    "llm": {
        "provider": "openai",
        "openai_api_key": "",
        "claude_api_key": "",
        "gemini_api_key": "",
    },
    "pinecone": {
        "api_key": "",
        "index_name_eq": "groww-instruments-eq",
    },
    "trading": {
        "live_default_mode": "paper",
        "live_default_refresh_seconds": 15,
        "live_default_stop_loss_pct": 2.0,
        "live_default_take_profit_pct": 4.0,
        "live_default_risk_per_trade_pct": 1.0,
        "live_default_max_position_pct": 10.0,
        "live_session_state_file": "data/runtime/live_session_state.json",
        "live_auto_resume_session": True,
        "kill_switch_enabled": False,
        "live_market_hours_only": True,
        "live_max_orders_per_day": 40,
        "order_journal_file": "data/runtime/order_journal.sqlite",
    },
    "visualization": {
        "default_period": "1mo",
        "default_interval": "1d",
        "default_chart_type": "candlestick",
    },
}


def _settings_file_path() -> Path:
    path_str = os.getenv(SETTINGS_FILE_ENV, DEFAULT_SETTINGS_FILE)
    return Path(path_str)


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y", "on"}


def _apply_cast(value: Any, cast_type: Optional[type]) -> Any:
    if cast_type is None:
        return value
    if cast_type is bool:
        return _parse_bool(value)
    if cast_type is int:
        return int(float(value))
    if cast_type is float:
        return float(value)
    if cast_type is str:
        return str(value)
    return cast_type(value)


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    return True


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _get_nested(data: Dict[str, Any], dotted_key: str) -> Any:
    current: Any = data
    for part in dotted_key.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _set_nested(data: Dict[str, Any], dotted_key: str, value: Any) -> Dict[str, Any]:
    parts = dotted_key.split(".")
    current = data
    for part in parts[:-1]:
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value
    return data


def load_settings() -> Dict[str, Any]:
    settings = deepcopy(DEFAULT_SETTINGS)
    path = _settings_file_path()
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                settings = _deep_merge(settings, payload)
        except (json.JSONDecodeError, OSError):
            return settings
    return settings


def save_settings(settings: Dict[str, Any]) -> bool:
    path = _settings_file_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
        return True
    except OSError:
        return False


def get_setting(dotted_key: str, default: Any = None, cast_type: Optional[type] = None) -> Any:
    settings = load_settings()
    value = _get_nested(settings, dotted_key)
    if _has_value(value):
        try:
            return _apply_cast(value, cast_type)
        except (TypeError, ValueError):
            pass

    env_key = ENV_MAPPING.get(dotted_key)
    if env_key:
        env_value = os.getenv(env_key)
        if _has_value(env_value):
            try:
                return _apply_cast(env_value, cast_type)
            except (TypeError, ValueError):
                pass

    return default


def set_setting(dotted_key: str, value: Any) -> bool:
    settings = load_settings()
    _set_nested(settings, dotted_key, value)
    return save_settings(settings)


def get_settings_file() -> str:
    return str(_settings_file_path())


def mask_secret(value: Optional[str], keep: int = 4) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if len(text) <= keep:
        return "*" * len(text)
    return ("*" * (len(text) - keep)) + text[-keep:]
