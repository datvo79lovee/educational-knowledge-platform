"""Ollama adapter dùng local HTTP API, không phụ thuộc SDK provider."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.evidence_review.provider import ProviderResult


class OllamaProvider:
    """Client tối thiểu cho ``/api/tags``, ``/api/show`` và ``/api/chat``."""

    def __init__(
        self,
        *,
        endpoint: str,
        model: str,
        expected_digest: str,
        temperature: float,
        seed: int,
        num_predict: int,
        timeout_seconds: float,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.expected_digest = expected_digest
        self.temperature = temperature
        self.seed = seed
        self.num_predict = num_predict
        self.timeout_seconds = timeout_seconds

    def _request(self, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.endpoint}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="GET" if payload is None else "POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise RuntimeError(f"Ollama request failed for {path}: {error}") from error

    def verify_runtime(self) -> dict[str, Any]:
        version = self._request("/api/version").get("version")
        tags = self._request("/api/tags").get("models", [])
        model_entry = next(
            (item for item in tags if item.get("name") == self.model), None
        )
        if model_entry is None:
            raise RuntimeError(f"Required local model is not installed: {self.model}")
        actual_digest = model_entry.get("digest")
        if actual_digest != self.expected_digest:
            raise RuntimeError(
                f"Ollama model digest mismatch: {actual_digest!r} != {self.expected_digest!r}"
            )
        details = model_entry.get("details", {})
        return {
            "ollama_version": version,
            "model": self.model,
            "digest": actual_digest,
            "size_bytes": model_entry.get("size"),
            "family": details.get("family"),
            "parameter_size": details.get("parameter_size"),
            "quantization_level": details.get("quantization_level"),
        }

    def review(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
    ) -> ProviderResult:
        response = self._request(
            "/api/chat",
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
                "format": output_schema,
                "options": {
                    "temperature": self.temperature,
                    "seed": self.seed,
                    "num_predict": self.num_predict,
                },
                "keep_alive": "5m",
            },
        )
        message = response.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise RuntimeError("Ollama response has no message.content string")
        return ProviderResult(
            content=message["content"],
            prompt_eval_count=response.get("prompt_eval_count"),
            eval_count=response.get("eval_count"),
        )

