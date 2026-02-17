from trade_engine.config.settings_store import get_setting, set_setting


def get_groww_api_key() -> str:
    return str(get_setting("broker.groww.api_key", "", str) or "").strip()


def get_groww_api_secret() -> str:
    return str(get_setting("broker.groww.api_secret", "", str) or "").strip()


def get_groww_access_token() -> str:
    return str(get_setting("broker.groww.access_token", "", str) or "").strip()


def set_groww_credentials(api_key: str, api_secret: str) -> bool:
    ok_key = set_setting("broker.groww.api_key", str(api_key or "").strip())
    ok_secret = set_setting("broker.groww.api_secret", str(api_secret or "").strip())
    return ok_key and ok_secret


def set_groww_access_token(access_token: str) -> bool:
    return set_setting("broker.groww.access_token", str(access_token or "").strip())


# Backward compatibility constants.
GROWW_API_KEY = get_groww_api_key()
GROWW_API_SECRET = get_groww_api_secret()
