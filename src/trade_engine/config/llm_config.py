from trade_engine.config.settings_store import get_setting, set_setting


def get_llm_provider() -> str:
    provider = str(get_setting("llm.provider", "openai", str) or "openai").strip().lower()
    if provider not in {"openai", "claude", "gemini"}:
        return "openai"
    return provider


def set_llm_provider(provider: str) -> bool:
    selected = str(provider or "").strip().lower()
    if selected not in {"openai", "claude", "gemini"}:
        raise ValueError(f"Unsupported provider '{provider}'. Supported: openai, claude, gemini")
    return set_setting("llm.provider", selected)


def get_openai_api_key() -> str:
    return str(get_setting("llm.openai_api_key", "", str) or "").strip()


def get_claude_api_key() -> str:
    return str(get_setting("llm.claude_api_key", "", str) or "").strip()


def get_gemini_api_key() -> str:
    return str(get_setting("llm.gemini_api_key", "", str) or "").strip()


def set_openai_api_key(api_key: str) -> bool:
    return set_setting("llm.openai_api_key", str(api_key or "").strip())


def set_claude_api_key(api_key: str) -> bool:
    return set_setting("llm.claude_api_key", str(api_key or "").strip())


def set_gemini_api_key(api_key: str) -> bool:
    return set_setting("llm.gemini_api_key", str(api_key or "").strip())


LLM_PROVIDER = get_llm_provider()

LLM_MODELS = {
    "openai": "gpt-4o",
    "claude": "claude-sonnet-4-5-20250929",
    "gemini": "gemini-pro",
}

DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 4096
