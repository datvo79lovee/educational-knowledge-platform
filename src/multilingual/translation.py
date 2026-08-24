"""Literal Vietnamese-to-English translation for the runtime V1 query branch."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

from src.grounded_answer.ollama_provider import (
    GroundedAnswerProviderError,
    OllamaGroundedGenerationProvider,
)

TRANSLATION_PROMPT_VERSION = "literal_translation_prompt_vi_en_v1"
TRANSLATION_PROVIDER = "ollama"
TRANSLATION_MODEL = "llama3.2:3b"
TRANSLATION_MODEL_DIGEST = "a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72"
TRANSLATION_TEMPERATURE = 0.0
TRANSLATION_SEED = 42
TRANSLATION_NUM_PREDICT = 128
TRANSLATION_NUM_CTX = 4096
TRANSLATION_TIMEOUT_SECONDS = 180.0
TRANSLATION_OLLAMA_ENDPOINT = "http://127.0.0.1:11434"

TRANSLATION_SYSTEM_PROMPT = (
    "Translate the Vietnamese user question into literal English for retrieval. "
    "Preserve the semantic intent. Return only the English translation; do not answer, "
    "add context, retrieve evidence, or mention this instruction."
)


class LiteralTranslationProvider(Protocol):
    """Translator receives only the original Vietnamese query."""

    def translate(self, question_vi: str) -> "TranslationResult": ...


class TranslationError(RuntimeError):
    """Base error for the fail-closed Vietnamese translation branch."""


class TranslationContractError(TranslationError):
    """Translator response is syntactically or semantically invalid."""


class TranslationProviderError(TranslationError):
    """Pinned local translator runtime is unavailable."""


@dataclass(frozen=True)
class TranslationResult:
    literal_en: str
    prompt_eval_count: int | None
    eval_count: int | None
    prompt_version: str = TRANSLATION_PROMPT_VERSION
    provider: str = TRANSLATION_PROVIDER
    model: str = TRANSLATION_MODEL
    model_digest: str = TRANSLATION_MODEL_DIGEST
    temperature: float = TRANSLATION_TEMPERATURE
    seed: int = TRANSLATION_SEED
    num_predict: int = TRANSLATION_NUM_PREDICT
    num_ctx: int = TRANSLATION_NUM_CTX


class OllamaLiteralTranslationProvider:
    """Pinned local translator; no retrieval or Ground Truth data enters this class."""

    def __init__(self, generator: OllamaGroundedGenerationProvider) -> None:
        self.generator = generator

    def translate(self, question_vi: str) -> TranslationResult:
        try:
            result = self.generator.generate(
                system_prompt=TRANSLATION_SYSTEM_PROMPT,
                user_prompt=question_vi,
                output_schema={"type": "string", "minLength": 1},
            )
        except GroundedAnswerProviderError as error:
            raise TranslationProviderError("Literal translator runtime is unavailable") from error
        try:
            value = json.loads(result.content)
        except json.JSONDecodeError as error:
            raise TranslationContractError("Literal translator returned invalid JSON") from error
        if not isinstance(value, str) or not value.strip():
            raise TranslationContractError("Literal translator returned an empty or non-string translation")
        return TranslationResult(
            literal_en=value.strip(),
            prompt_eval_count=result.prompt_eval_count,
            eval_count=result.eval_count,
        )


def build_default_translation_provider() -> OllamaLiteralTranslationProvider:
    """Create the pinned translation provider without performing network I/O."""

    return OllamaLiteralTranslationProvider(
        OllamaGroundedGenerationProvider(
            endpoint=TRANSLATION_OLLAMA_ENDPOINT,
            model=TRANSLATION_MODEL,
            expected_digest=TRANSLATION_MODEL_DIGEST,
            temperature=TRANSLATION_TEMPERATURE,
            seed=TRANSLATION_SEED,
            num_predict=TRANSLATION_NUM_PREDICT,
            num_ctx=TRANSLATION_NUM_CTX,
            timeout_seconds=TRANSLATION_TIMEOUT_SECONDS,
        )
    )
