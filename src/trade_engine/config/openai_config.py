from trade_engine.config.settings_store import get_setting, set_setting


def get_openai_api_key() -> str:
    return str(get_setting("llm.openai_api_key", "", str) or "").strip()


def set_openai_api_key(api_key: str) -> bool:
    return set_setting("llm.openai_api_key", str(api_key or "").strip())


OPENAI_API_KEY = get_openai_api_key()
OPENAI_EMBEDDING_MODEL = "text-embedding-3-large"
OPENAI_EMBEDDING_DIMENSION = 1024
