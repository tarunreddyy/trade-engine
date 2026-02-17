from trade_engine.config.settings_store import get_setting, set_setting


def get_pinecone_api_key() -> str:
    return str(get_setting("pinecone.api_key", "", str) or "").strip()


def set_pinecone_api_key(api_key: str) -> bool:
    return set_setting("pinecone.api_key", str(api_key or "").strip())


def get_pinecone_index_name_eq() -> str:
    return str(get_setting("pinecone.index_name_eq", "groww-instruments-eq", str) or "groww-instruments-eq").strip()


def set_pinecone_index_name_eq(index_name: str) -> bool:
    value = str(index_name or "").strip() or "groww-instruments-eq"
    return set_setting("pinecone.index_name_eq", value)


PINECONE_API_KEY = get_pinecone_api_key()
PINECONE_INDEX_NAME_EQ = get_pinecone_index_name_eq()
