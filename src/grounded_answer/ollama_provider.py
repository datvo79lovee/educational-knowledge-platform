"""Ollama adapter riêng cho Grounded Answer Generator."""

from __future__ import annotations

import json
from threading import Lock
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.grounded_answer.provider import GenerationProviderResult


class GroundedAnswerProviderError(RuntimeError):
    """Ollama unavailable hoặc response transport không hợp lệ."""


class OllamaGroundedGenerationProvider:
    """Client local tối thiểu; không tải model và không phụ thuộc provider SDK."""

    def __init__(
        self,
        *,
        endpoint: str,
        model: str,
        expected_digest: str,
        temperature: float,
        seed: int,
        num_predict: int,
        num_ctx: int,
        timeout_seconds: float,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.expected_digest = expected_digest
        self.temperature = temperature
        self.seed = seed
        self.num_predict = num_predict
        self.num_ctx = num_ctx
        self.timeout_seconds = timeout_seconds
        self._verification_lock = Lock()
        self._verified_runtime: dict[str, Any] | None = None

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
            raise GroundedAnswerProviderError(
                f"Ollama request failed for {path}: {error}"
            ) from error

    def verify_runtime(self) -> dict[str, Any]:
        with self._verification_lock:
            version = self._request("/api/version").get("version")
            models = self._request("/api/tags").get("models", [])
            model_entry = next(
                (item for item in models if item.get("name") == self.model), None
            )
            if model_entry is None:
                raise GroundedAnswerProviderError(
                    f"Required local model is not installed: {self.model}"
                )
            actual_digest = model_entry.get("digest")
            if actual_digest != self.expected_digest:
                raise GroundedAnswerProviderError(
                    f"Ollama model digest mismatch: {actual_digest!r} != "
                    f"{self.expected_digest!r}"
                )
            details = model_entry.get("details", {})
            runtime = {
                "ollama_version": version,
                "model": self.model,
                "digest": actual_digest,
                "size_bytes": model_entry.get("size"),
                "family": details.get("family"),
                "parameter_size": details.get("parameter_size"),
                "quantization_level": details.get("quantization_level"),
            }
            self._verified_runtime = runtime
            return dict(runtime)

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
    ) -> GenerationProviderResult:
        """Thực hiện đúng một `/api/chat` call, không retry hoặc auto-repair."""

        if self._verified_runtime is None:
            self.verify_runtime()
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
                    "num_ctx": self.num_ctx,
                },
                "keep_alive": "5m",
            },
        )
        message = response.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise GroundedAnswerProviderError(
                "Ollama response has no message.content string"
            )
        return GenerationProviderResult(
            content=message["content"],
            prompt_eval_count=response.get("prompt_eval_count"),
            eval_count=response.get("eval_count"),
        )

    def inspect_process(self) -> dict[str, Any] | None:
        models = self._request("/api/ps").get("models", [])
        process = next(
            (
                row
                for row in models
                if row.get("name") == self.model or row.get("model") == self.model
            ),
            None,
        )
        if process is None:
            return None
        return {
            "model": process.get("name") or process.get("model"),
            "digest": process.get("digest"),
            "size_bytes": process.get("size"),
            "size_vram_bytes": process.get("size_vram"),
            "context_length": process.get("context_length"),
        }
