"""Strict contracts cho model output và public Grounded Answer API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    """Từ chối field ngoài contract để tránh sửa ngầm model output."""

    model_config = ConfigDict(extra="forbid")


class GroundedAnswerRequest(StrictModel):
    """Client chỉ gửi question; evidence luôn do DenseSearchService lấy."""

    question: str = Field(min_length=1)

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("question must not be empty or whitespace-only")
        return normalized


class ModelGroundedDecision(StrictModel):
    """Bốn field duy nhất mà local LLM được phép quyết định."""

    decision: Literal["answer", "abstain"]
    answer: str | None
    supporting_chunk_ids: list[str] = Field(max_length=3)
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("answer")
    @classmethod
    def normalize_answer(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("answer must not be empty or whitespace-only")
        return normalized

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("reason must not be empty or whitespace-only")
        return normalized

    @model_validator(mode="after")
    def validate_decision_shape(self) -> "ModelGroundedDecision":
        if len(self.supporting_chunk_ids) != len(set(self.supporting_chunk_ids)):
            raise ValueError("supporting_chunk_ids must be unique")
        if self.decision == "answer":
            if self.answer is None:
                raise ValueError("answer decision requires a non-null answer")
            if not self.supporting_chunk_ids:
                raise ValueError("answer decision requires at least one supporting chunk")
        else:
            if self.answer is not None:
                raise ValueError("abstain decision requires answer=null")
            if self.supporting_chunk_ids:
                raise ValueError("abstain decision requires no supporting chunks")
        return self


def validate_supporting_chunk_subset(
    decision: ModelGroundedDecision,
    candidate_chunk_ids: list[str],
) -> None:
    """Từ chối mọi ID không thuộc Dense Top 3 của chính request."""

    outside_ids = set(decision.supporting_chunk_ids) - set(candidate_chunk_ids)
    if outside_ids:
        raise ValueError(
            "Model returned chunk IDs outside this request's Dense Top 3: "
            + ", ".join(sorted(outside_ids))
        )


def build_model_output_schema(candidate_chunk_ids: list[str]) -> dict[str, Any]:
    """Tạo structured-output schema động, khóa IDs vào Top 3 hiện tại."""

    if len(candidate_chunk_ids) != 3 or len(set(candidate_chunk_ids)) != 3:
        raise ValueError("Model output schema requires exactly three unique candidate IDs")
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": ["decision", "answer", "supporting_chunk_ids", "reason"],
        "properties": {
            "decision": {"enum": ["answer", "abstain"]},
            "answer": {"type": ["string", "null"]},
            "supporting_chunk_ids": {
                "type": "array",
                "items": {"enum": candidate_chunk_ids},
                "maxItems": 3,
                "uniqueItems": True,
            },
            "reason": {"type": "string", "minLength": 1, "maxLength": 500},
        },
        "allOf": [
            {
                "if": {"properties": {"decision": {"const": "abstain"}}},
                "then": {
                    "properties": {
                        "answer": {"type": "null"},
                        "supporting_chunk_ids": {"maxItems": 0},
                    }
                },
            }
        ],
    }


class Citation(StrictModel):
    """Citation được application map từ canonical retrieval metadata."""

    chunk_id: str
    rank: int = Field(ge=1, le=3)
    video_id: str
    video_url: str
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    citation_url: str

    @model_validator(mode="after")
    def validate_time_range(self) -> "Citation":
        if self.end <= self.start:
            raise ValueError("citation end must be greater than start")
        return self


class RetrievalTrace(StrictModel):
    """Identity tối thiểu của retrieval branch public API sử dụng."""

    method: Literal["dense_baseline_v1"]
    top_k: Literal[3]


class GroundedAnswerResponse(StrictModel):
    """Public response; không expose model-generated diagnostic reason."""

    question: str
    decision: Literal["answer", "abstain"]
    answer: str | None
    supporting_chunk_ids: list[str] = Field(max_length=3)
    citations: list[Citation] = Field(max_length=3)
    retrieval: RetrievalTrace

    @model_validator(mode="after")
    def validate_response_shape(self) -> "GroundedAnswerResponse":
        if len(self.supporting_chunk_ids) != len(set(self.supporting_chunk_ids)):
            raise ValueError("supporting_chunk_ids must be unique")
        citation_ids = [citation.chunk_id for citation in self.citations]
        if citation_ids != self.supporting_chunk_ids:
            raise ValueError("citations must match supporting IDs in retrieval-rank order")
        if self.decision == "answer":
            if self.answer is None or not self.answer.strip():
                raise ValueError("answer response requires a non-empty answer")
            if not self.supporting_chunk_ids:
                raise ValueError("answer response requires supporting chunks")
        elif self.answer is not None or self.supporting_chunk_ids or self.citations:
            raise ValueError("abstain response requires null answer and empty evidence")
        return self
