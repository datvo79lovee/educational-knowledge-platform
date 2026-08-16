"""Contract nội bộ cho output cốt lõi của evidence reviewer."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReviewerDecision(BaseModel):
    """Ba trường duy nhất mà model được phép quyết định."""

    model_config = ConfigDict(extra="forbid")

    decision: Literal["accept", "reject"]
    decision_reason: str = Field(min_length=1)
    supporting_chunk_ids: list[str]

    @model_validator(mode="after")
    def validate_decision_shape(self) -> "ReviewerDecision":
        if len(self.supporting_chunk_ids) != len(set(self.supporting_chunk_ids)):
            raise ValueError("supporting_chunk_ids must be unique")
        if self.decision == "accept" and not self.supporting_chunk_ids:
            raise ValueError("accept requires at least one supporting chunk")
        if self.decision == "reject" and self.supporting_chunk_ids:
            raise ValueError("reject requires an empty supporting_chunk_ids list")
        return self


def validate_candidate_subset(
    decision: ReviewerDecision, candidate_chunk_ids: list[str]
) -> None:
    """Chặn model viện dẫn evidence nằm ngoài candidate pool đã khóa."""

    outside_ids = set(decision.supporting_chunk_ids) - set(candidate_chunk_ids)
    if outside_ids:
        raise ValueError(
            "Reviewer returned chunk IDs outside Dense Top 3: "
            + ", ".join(sorted(outside_ids))
        )

