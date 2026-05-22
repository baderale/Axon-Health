"""OpenAI-compatible client facade over the Model Registry.

Agents never instantiate inference clients directly. They call
``get_client(logical_name)`` and the registry decides which backend, weights,
system prompt, and parameters to use. The Ollama and vLLM backends both
expose OpenAI-compatible chat-completion endpoints, so a single facade works.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from axon.model_registry.registry import Backend, ModelSpec, resolve


@dataclass
class _BackendEndpoint:
    base_url: str
    api_key: str


def _endpoint_for(backend: Backend) -> _BackendEndpoint:
    if backend is Backend.OLLAMA:
        return _BackendEndpoint(
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434/v1"),
            api_key=os.environ.get("OLLAMA_API_KEY", "ollama"),
        )
    if backend is Backend.VLLM:
        return _BackendEndpoint(
            base_url=os.environ.get("VLLM_BASE_URL", "http://vllm:8000/v1"),
            api_key=os.environ.get("VLLM_API_KEY", "vllm"),
        )
    raise ValueError(f"Unsupported backend: {backend!r}")


class ModelClient:
    """Thin wrapper that binds an OpenAI client to a logical model spec."""

    def __init__(self, spec: ModelSpec) -> None:
        self.spec = spec
        endpoint = _endpoint_for(spec.backend)
        self._client = OpenAI(base_url=endpoint.base_url, api_key=endpoint.api_key)

    def chat(self, user_message: str, *, extra_context: str | None = None) -> str:
        """Single-turn chat. Returns the assistant text."""
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.spec.system_prompt},
        ]
        if extra_context:
            messages.append({"role": "system", "content": f"Context:\n{extra_context}"})
        messages.append({"role": "user", "content": user_message})

        response = self._client.chat.completions.create(
            model=self.spec.base_model,
            messages=messages,
            temperature=self.spec.temperature,
            max_tokens=self.spec.max_tokens,
        )
        return response.choices[0].message.content or ""


def get_client(logical_name: str) -> ModelClient:
    return ModelClient(resolve(logical_name))
