from trade_engine.config.settings_store import get_setting, set_setting

SUPPORTED_BROKERS = ("groww", "upstox", "zerodha")


def get_active_broker() -> str:
    broker = str(get_setting("broker.active", "groww", str) or "groww").strip().lower()
    if broker not in SUPPORTED_BROKERS:
        return "groww"
    return broker


def set_active_broker(broker_name: str) -> bool:
    selected = str(broker_name or "").strip().lower()
    if selected not in SUPPORTED_BROKERS:
        supported = ", ".join(SUPPORTED_BROKERS)
        raise ValueError(f"Unsupported broker '{broker_name}'. Supported: {supported}")
    return set_setting("broker.active", selected)


# Backward compatibility for modules that still import constants.
ACTIVE_BROKER = get_active_broker()
