from abc import ABC, abstractmethod

from trade_engine.config.llm_config import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    LLM_MODELS,
    get_claude_api_key,
    get_gemini_api_key,
    get_openai_api_key,
)


class BaseLLMClient(ABC):
    """Abstract base for LLM provider clients."""

    @abstractmethod
    def generate_completion(self, messages, temperature=None, max_tokens=None) -> str:
        """Generate a text completion from a list of messages."""


class OpenAIClient(BaseLLMClient):
    def __init__(self):
        from openai import OpenAI

        self.client = OpenAI(api_key=get_openai_api_key())
        self.model = LLM_MODELS["openai"]

    def generate_completion(self, messages, temperature=None, max_tokens=None) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature or DEFAULT_TEMPERATURE,
            max_tokens=max_tokens or DEFAULT_MAX_TOKENS,
        )
        return response.choices[0].message.content


class ClaudeClient(BaseLLMClient):
    def __init__(self):
        import anthropic

        self.client = anthropic.Anthropic(api_key=get_claude_api_key())
        self.model = LLM_MODELS["claude"]

    def generate_completion(self, messages, temperature=None, max_tokens=None) -> str:
        system_msg = ""
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                user_messages.append({"role": msg["role"], "content": msg["content"]})

        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens or DEFAULT_MAX_TOKENS,
            "messages": user_messages,
            "temperature": temperature if temperature is not None else DEFAULT_TEMPERATURE,
        }
        if system_msg:
            kwargs["system"] = system_msg

        response = self.client.messages.create(**kwargs)
        return response.content[0].text


class GeminiClient(BaseLLMClient):
    def __init__(self):
        import google.generativeai as genai

        genai.configure(api_key=get_gemini_api_key())
        self.model = genai.GenerativeModel(LLM_MODELS["gemini"])

    def generate_completion(self, messages, temperature=None, max_tokens=None) -> str:
        parts = []
        for msg in messages:
            prefix = "System" if msg["role"] == "system" else msg["role"].capitalize()
            parts.append(f"{prefix}: {msg['content']}")
        prompt = "\n\n".join(parts)

        config = {
            "temperature": temperature or DEFAULT_TEMPERATURE,
            "max_output_tokens": max_tokens or DEFAULT_MAX_TOKENS,
        }
        response = self.model.generate_content(prompt, generation_config=config)
        return response.text


class LLMFactory:
    """Factory to create the appropriate LLM client."""

    _clients = {
        "openai": OpenAIClient,
        "claude": ClaudeClient,
        "gemini": GeminiClient,
    }

    @staticmethod
    def create_llm_client(provider: str) -> BaseLLMClient:
        selected = provider.lower()
        if selected not in LLMFactory._clients:
            supported = list(LLMFactory._clients.keys())
            raise ValueError(f"Unknown LLM provider '{provider}'. Choose from: {supported}")
        return LLMFactory._clients[selected]()
