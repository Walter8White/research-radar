import os
from abc import ABC, abstractmethod
from typing import Optional

import requests
from dotenv import dotenv_values
from openai import OpenAI


LLM_PROVIDERS = ["OpenAI", "Claude", "Disabled"]
DEFAULT_LLM_PROVIDER = "OpenAI"
ENV_PATH = ".env"


def normalize_provider(value: Optional[str]) -> str:
    if value in LLM_PROVIDERS:
        return value

    return DEFAULT_LLM_PROVIDER


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 900) -> str:
        raise NotImplementedError

    @abstractmethod
    def test_connection(self) -> tuple[bool, str]:
        raise NotImplementedError


class NoLLMProvider(LLMProvider):
    def generate(self, prompt: str, max_tokens: int = 900) -> str:
        raise RuntimeError("LLM provider is disabled.")

    def test_connection(self) -> tuple[bool, str]:
        return True, "LLM disabled. Deterministic fallback will be used."


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def generate(self, prompt: str, max_tokens: int = 900) -> str:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")

        client = OpenAI(api_key=self.api_key)
        response = client.responses.create(
            model=self.model,
            input=prompt,
            max_output_tokens=max_tokens,
        )
        return response.output_text.strip()

    def test_connection(self) -> tuple[bool, str]:
        if not self.api_key:
            return False, "OPENAI_API_KEY is not set."

        try:
            text = self.generate("Reply with: OK", max_tokens=16)
        except Exception as exc:
            return False, f"OpenAI test failed: {exc}"

        return True, f"OpenAI connected ({self.model}): {text[:40]}"


class ClaudeProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def generate(self, prompt: str, max_tokens: int = 900) -> str:
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set.")

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        return "".join(
            block.get("text", "")
            for block in data.get("content", [])
            if block.get("type") == "text"
        ).strip()

    def test_connection(self) -> tuple[bool, str]:
        if not self.api_key:
            return False, "ANTHROPIC_API_KEY is not set."

        try:
            text = self.generate("Reply with: OK", max_tokens=16)
        except Exception as exc:
            return False, f"Claude test failed: {exc}"

        return True, f"Claude connected ({self.model}): {text[:40]}"


def local_env_values() -> dict:
    values = {key: value for key, value in os.environ.items()}
    values.update(
        {
            key: value
            for key, value in dotenv_values(ENV_PATH).items()
            if value is not None
        }
    )
    return values


def provider_from_env() -> LLMProvider:
    env = local_env_values()
    provider = normalize_provider(env.get("LLM_PROVIDER", DEFAULT_LLM_PROVIDER))

    if provider == "OpenAI":
        return OpenAIProvider(
            api_key=env.get("OPENAI_API_KEY", ""),
            model=env.get("OPENAI_MODEL", "gpt-5.4"),
        )

    if provider == "Claude":
        return ClaudeProvider(
            api_key=env.get("ANTHROPIC_API_KEY", ""),
            model=env.get("CLAUDE_MODEL", "claude-sonnet-4-20250514"),
        )

    return NoLLMProvider()
