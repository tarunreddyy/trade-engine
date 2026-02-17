import os
from dotenv import load_dotenv

load_dotenv()

# LLM Provider: "openai", "claude", or "gemini"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Model names
LLM_MODELS = {
    "openai": "gpt-4o",
    "claude": "claude-sonnet-4-5-20250929",
    "gemini": "gemini-pro",
}

# Default generation params
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 4096


