"""Provider-neutral interface cho một model call grounded generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class GenerationProviderResult:
    """Raw structured content và token counters để audit runtime."""

    content: str
    prompt_eval_count: int | None
    eval_count: int | None


class GroundedGenerationProvider(Protocol):
    """Interface nhỏ để test contract mà không gọi model thật."""

    def verify_runtime(self) -> dict[str, Any]: ...

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
    ) -> GenerationProviderResult: ...
