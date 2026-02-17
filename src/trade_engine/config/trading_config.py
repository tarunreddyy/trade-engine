from trade_engine.config.settings_store import get_setting, set_setting


def get_live_default_mode() -> str:
    mode = str(get_setting("trading.live_default_mode", "paper", str) or "paper").strip().lower()
    return mode if mode in {"paper", "live"} else "paper"


def set_live_default_mode(mode: str) -> bool:
    selected = str(mode or "").strip().lower()
    if selected not in {"paper", "live"}:
        raise ValueError("live_default_mode must be 'paper' or 'live'")
    return set_setting("trading.live_default_mode", selected)


def get_live_default_refresh_seconds() -> int:
    return max(3, int(get_setting("trading.live_default_refresh_seconds", 15, int)))


def set_live_default_refresh_seconds(seconds: int) -> bool:
    return set_setting("trading.live_default_refresh_seconds", max(3, int(seconds)))


def get_live_default_stop_loss_pct() -> float:
    return max(0.1, float(get_setting("trading.live_default_stop_loss_pct", 2.0, float)))


def set_live_default_stop_loss_pct(value: float) -> bool:
    return set_setting("trading.live_default_stop_loss_pct", max(0.1, float(value)))


def get_live_default_take_profit_pct() -> float:
    return max(0.1, float(get_setting("trading.live_default_take_profit_pct", 4.0, float)))


def set_live_default_take_profit_pct(value: float) -> bool:
    return set_setting("trading.live_default_take_profit_pct", max(0.1, float(value)))


def get_live_default_risk_per_trade_pct() -> float:
    return max(0.1, float(get_setting("trading.live_default_risk_per_trade_pct", 1.0, float)))


def set_live_default_risk_per_trade_pct(value: float) -> bool:
    return set_setting("trading.live_default_risk_per_trade_pct", max(0.1, float(value)))


def get_live_default_max_position_pct() -> float:
    return max(1.0, float(get_setting("trading.live_default_max_position_pct", 10.0, float)))


def set_live_default_max_position_pct(value: float) -> bool:
    return set_setting("trading.live_default_max_position_pct", max(1.0, float(value)))


def get_live_session_state_file() -> str:
    value = str(
        get_setting("trading.live_session_state_file", "data/runtime/live_session_state.json", str)
        or "data/runtime/live_session_state.json"
    ).strip()
    return value or "data/runtime/live_session_state.json"


def set_live_session_state_file(path: str) -> bool:
    value = str(path or "").strip() or "data/runtime/live_session_state.json"
    return set_setting("trading.live_session_state_file", value)


def get_live_auto_resume_session() -> bool:
    return bool(get_setting("trading.live_auto_resume_session", True, bool))


def set_live_auto_resume_session(value: bool) -> bool:
    return set_setting("trading.live_auto_resume_session", bool(value))


def get_kill_switch_enabled() -> bool:
    return bool(get_setting("trading.kill_switch_enabled", False, bool))


def set_kill_switch_enabled(value: bool) -> bool:
    return set_setting("trading.kill_switch_enabled", bool(value))


def get_live_market_hours_only() -> bool:
    return bool(get_setting("trading.live_market_hours_only", True, bool))


def set_live_market_hours_only(value: bool) -> bool:
    return set_setting("trading.live_market_hours_only", bool(value))


def get_live_max_orders_per_day() -> int:
    return max(1, int(get_setting("trading.live_max_orders_per_day", 40, int)))


def set_live_max_orders_per_day(value: int) -> bool:
    return set_setting("trading.live_max_orders_per_day", max(1, int(value)))


def get_order_journal_file() -> str:
    value = str(
        get_setting("trading.order_journal_file", "data/runtime/order_journal.sqlite", str)
        or "data/runtime/order_journal.sqlite"
    ).strip()
    return value or "data/runtime/order_journal.sqlite"


def set_order_journal_file(path: str) -> bool:
    value = str(path or "").strip() or "data/runtime/order_journal.sqlite"
    return set_setting("trading.order_journal_file", value)


# Backward compatibility constants.
LIVE_DEFAULT_MODE = get_live_default_mode()
LIVE_DEFAULT_REFRESH_SECONDS = get_live_default_refresh_seconds()
LIVE_DEFAULT_STOP_LOSS_PCT = get_live_default_stop_loss_pct()
LIVE_DEFAULT_TAKE_PROFIT_PCT = get_live_default_take_profit_pct()
LIVE_DEFAULT_RISK_PER_TRADE_PCT = get_live_default_risk_per_trade_pct()
LIVE_DEFAULT_MAX_POSITION_PCT = get_live_default_max_position_pct()
LIVE_SESSION_STATE_FILE = get_live_session_state_file()
LIVE_AUTO_RESUME_SESSION = get_live_auto_resume_session()
KILL_SWITCH_ENABLED = get_kill_switch_enabled()
LIVE_MARKET_HOURS_ONLY = get_live_market_hours_only()
LIVE_MAX_ORDERS_PER_DAY = get_live_max_orders_per_day()
ORDER_JOURNAL_FILE = get_order_journal_file()
