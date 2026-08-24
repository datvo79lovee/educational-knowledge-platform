"""Orchestration: Dense Top 3 -> one model call -> code-owned citations."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from src.grounded_answer.contracts import (
    Citation,
    GroundedAnswerResponse,
    ModelGroundedDecision,
    RetrievalTrace,
    build_model_output_schema,
    validate_supporting_chunk_subset,
)
from src.grounded_answer.ollama_provider import OllamaGroundedGenerationProvider
from src.grounded_answer.prompts import SYSTEM_PROMPT, VI_SYSTEM_PROMPT, build_user_prompt
from src.grounded_answer.provider import GroundedGenerationProvider
from src.multilingual.translation import LiteralTranslationProvider, TranslationError
from src.search_api.service import DenseSearchService, RETRIEVAL_METHOD, TOP_K


PROVIDER = "ollama"
MODEL = "llama3.2:3b"
MODEL_DIGEST = "a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72"
OLLAMA_ENDPOINT = "http://127.0.0.1:11434"
TEMPERATURE = 0.0
SEED = 42
NUM_CTX = 4096
NUM_PREDICT = 512
TIMEOUT_SECONDS = 180.0
MODEL_OUTPUT_SCHEMA_VERSION = "grounded_answer_model_output_v1"
API_SCHEMA_VERSION = "grounded_answer_api_v1"


class GroundedAnswerContractError(ValueError):
    """Model output sai schema hoặc trỏ ra ngoài Top 3."""


@dataclass(frozen=True)
class ModelOutputNormalization:
    """Raw/normalized payload và lý do canonicalization nội bộ."""

    raw_model_output: Any
    normalized_output: Any
    normalization_applied: bool
    normalization_reason: str | None


def normalize_model_output(
    raw_model_output: Any,
    candidate_chunk_ids: list[str],
) -> ModelOutputNormalization:
    """Chỉ canonicalize hai representation-noise cases đã được duyệt."""

    normalized_output = copy.deepcopy(raw_model_output)
    if not isinstance(raw_model_output, dict):
        return ModelOutputNormalization(
            raw_model_output=raw_model_output,
            normalized_output=normalized_output,
            normalization_applied=False,
            normalization_reason=None,
        )

    decision = raw_model_output.get("decision")
    answer = raw_model_output.get("answer")
    supporting_ids = raw_model_output.get("supporting_chunk_ids")
    if decision == "abstain" and answer == "abstain" and supporting_ids == []:
        normalized_output["answer"] = None
        return ModelOutputNormalization(
            raw_model_output=raw_model_output,
            normalized_output=normalized_output,
            normalization_applied=True,
            normalization_reason="abstain_literal_to_null",
        )

    if (
        decision == "answer"
        and isinstance(answer, str)
        and bool(answer.strip())
        and isinstance(supporting_ids, list)
        and all(isinstance(chunk_id, str) for chunk_id in supporting_ids)
        and len(supporting_ids) != len(set(supporting_ids))
        and set(supporting_ids).issubset(set(candidate_chunk_ids))
    ):
        normalized_output["supporting_chunk_ids"] = list(dict.fromkeys(supporting_ids))
        return ModelOutputNormalization(
            raw_model_output=raw_model_output,
            normalized_output=normalized_output,
            normalization_applied=True,
            normalization_reason="duplicate_supporting_ids",
        )

    return ModelOutputNormalization(
        raw_model_output=raw_model_output,
        normalized_output=normalized_output,
        normalization_applied=False,
        normalization_reason=None,
    )


@dataclass(frozen=True)
class GroundedAnswerExecution:
    """Public response cùng diagnostic nội bộ, không expose reason qua API."""

    response: GroundedAnswerResponse
    reason: str
    top3_chunk_ids: list[str]
    index_run_id: str
    prompt_eval_count: int | None
    eval_count: int | None
    raw_model_output: Any
    normalized_output: Any
    normalization_applied: bool
    normalization_reason: str | None
    translation_call_count: int
    translation_prompt_version: str | None
    translation_prompt_eval_count: int | None
    translation_eval_count: int | None


class GroundedAnswerService:
    """EN: one generation call; VI: one translation call then one generation call."""

    def __init__(
        self,
        *,
        search_service: DenseSearchService,
        provider: GroundedGenerationProvider,
        translator: LiteralTranslationProvider | None = None,
    ) -> None:
        self.search_service = search_service
        self.provider = provider
        self.translator = translator

    def answer(self, question: str, answer_language: str = "en") -> GroundedAnswerExecution:
        original_query = question.strip()
        translation = None
        if answer_language == "vi":
            if self.translator is None:
                raise TranslationError("Vietnamese runtime translator is not configured")
            translation = self.translator.translate(original_query)
            retrieval_query = translation.literal_en
        else:
            retrieval_query = original_query
        candidates = self.search_service.search(retrieval_query)
        if len(candidates) != TOP_K:
            raise RuntimeError(f"Dense retrieval returned {len(candidates)} results, expected 3")
        top3_ids = [str(candidate["chunk_id"]) for candidate in candidates]
        if len(set(top3_ids)) != TOP_K:
            raise RuntimeError("Dense retrieval returned duplicate Top 3 chunk IDs")

        provider_result = self.provider.generate(
            system_prompt=VI_SYSTEM_PROMPT if answer_language == "vi" else SYSTEM_PROMPT,
            user_prompt=build_user_prompt(original_query, candidates, answer_language),
            output_schema=build_model_output_schema(top3_ids),
        )
        try:
            raw_decision = json.loads(provider_result.content)
            normalization = normalize_model_output(raw_decision, top3_ids)
            decision = ModelGroundedDecision.model_validate(normalization.normalized_output)
            validate_supporting_chunk_subset(decision, top3_ids)
        except (json.JSONDecodeError, ValidationError, ValueError, TypeError) as error:
            raise GroundedAnswerContractError(
                f"Grounded answer model output failed strict validation: {error}"
            ) from error

        selected = set(decision.supporting_chunk_ids)
        selected_candidates = [
            candidate for candidate in candidates if candidate["chunk_id"] in selected
        ]
        canonical_ids = [str(candidate["chunk_id"]) for candidate in selected_candidates]
        citations = [
            Citation(
                chunk_id=str(candidate["chunk_id"]),
                rank=int(candidate["rank"]),
                video_id=str(candidate["video_id"]),
                video_url=str(candidate["source_url"]),
                start=float(candidate["start_second"]),
                end=float(candidate["end_second"]),
                citation_url=str(candidate["citation_url"]),
            )
            for candidate in selected_candidates
        ]
        response = GroundedAnswerResponse(
            question=original_query,
            original_query=original_query,
            retrieval_query=retrieval_query,
            answer_language=answer_language,
            decision=decision.decision,
            answer=decision.answer,
            supporting_chunk_ids=canonical_ids,
            citations=citations,
            retrieval=RetrievalTrace(method=RETRIEVAL_METHOD, top_k=TOP_K),
        )
        return GroundedAnswerExecution(
            response=response,
            reason=decision.reason,
            top3_chunk_ids=top3_ids,
            index_run_id=self.search_service.index_run_id,
            prompt_eval_count=provider_result.prompt_eval_count,
            eval_count=provider_result.eval_count,
            raw_model_output=normalization.raw_model_output,
            normalized_output=normalization.normalized_output,
            normalization_applied=normalization.normalization_applied,
            normalization_reason=normalization.normalization_reason,
            translation_call_count=1 if translation is not None else 0,
            translation_prompt_version=translation.prompt_version if translation else None,
            translation_prompt_eval_count=translation.prompt_eval_count if translation else None,
            translation_eval_count=translation.eval_count if translation else None,
        )


def build_default_provider() -> OllamaGroundedGenerationProvider:
    """Khởi tạo provider không I/O; `/search` vẫn startup khi Ollama chưa sẵn sàng."""

    return OllamaGroundedGenerationProvider(
        endpoint=OLLAMA_ENDPOINT,
        model=MODEL,
        expected_digest=MODEL_DIGEST,
        temperature=TEMPERATURE,
        seed=SEED,
        num_predict=NUM_PREDICT,
        num_ctx=NUM_CTX,
        timeout_seconds=TIMEOUT_SECONDS,
    )
