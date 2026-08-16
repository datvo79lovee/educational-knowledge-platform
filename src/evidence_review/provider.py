"""Giao diện provider-neutral cho evidence reviewer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ProviderResult:
    """Kết quả thô tối thiểu cần để validate và audit runtime."""

    content: str
    prompt_eval_count: int | None
    eval_count: int | None


class EvidenceReviewProvider(Protocol):
    """Provider khác có thể thay Ollama mà không đổi benchmark package."""

    def verify_runtime(self) -> dict[str, Any]: ...

    def review(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
    ) -> ProviderResult: ...

