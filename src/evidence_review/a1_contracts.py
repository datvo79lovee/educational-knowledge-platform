"""Internal contracts and deterministic reducer for the A1 two-stage reviewer."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.evidence_review.contracts import ReviewerDecision


class A1Requirement(BaseModel):
    """One essential requirement derived only from the question wording."""

    model_config = ConfigDict(extra="forbid")

    requirement_id: str = Field(pattern=r"^r[1-8]$")
    requirement: str = Field(min_length=1)


class A1RequirementAnalysis(BaseModel):
    """Stage 1 output; every listed requirement is essential."""

    model_config = ConfigDict(extra="forbid")

    requirements: list[A1Requirement] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def validate_unique_sequential_requirements(self) -> "A1RequirementAnalysis":
        requirement_ids = [row.requirement_id for row in self.requirements]
        expected_ids = [f"r{index}" for index in range(1, len(self.requirements) + 1)]
        if requirement_ids != expected_ids:
            raise ValueError("requirement IDs must be sequential r1..rN")
        normalized = [" ".join(row.requirement.lower().split()) for row in self.requirements]
        if len(normalized) != len(set(normalized)):
            raise ValueError("requirements must be unique")
        return self


class A1RequirementEntailment(BaseModel):
    """Stage 2 verdict for one requirement; no final question decision is allowed."""

    model_config = ConfigDict(extra="forbid")

    requirement_id: str = Field(pattern=r"^r[1-8]$")
    supported: bool
    supporting_chunk_ids: list[str]
    entailment_reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_support_shape(self) -> "A1RequirementEntailment":
        if len(self.supporting_chunk_ids) != len(set(self.supporting_chunk_ids)):
            raise ValueError("supporting_chunk_ids must be unique per requirement")
        if self.supported and not self.supporting_chunk_ids:
            raise ValueError("supported=true requires at least one supporting chunk")
        if not self.supported and self.supporting_chunk_ids:
            raise ValueError("supported=false requires no supporting chunks")
        return self


class A1EntailmentAnalysis(BaseModel):
    """Stage 2 output covering every Stage 1 requirement exactly once."""

    model_config = ConfigDict(extra="forbid")

    assessments: list[A1RequirementEntailment] = Field(min_length=1, max_length=8)


def canonicalize_entailment_payload(
    payload: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    """Deduplicate repeated supporting IDs without adding or reordering evidence."""

    canonical = deepcopy(payload)
    duplicate_count = 0
    assessments = canonical.get("assessments")
    if not isinstance(assessments, list):
        return canonical, duplicate_count
    for assessment in assessments:
        if not isinstance(assessment, dict):
            continue
        chunk_ids = assessment.get("supporting_chunk_ids")
        if not isinstance(chunk_ids, list):
            continue
        unique_ids: list[Any] = []
        seen: set[str] = set()
        for chunk_id in chunk_ids:
            if isinstance(chunk_id, str) and chunk_id in seen:
                duplicate_count += 1
                continue
            unique_ids.append(chunk_id)
            if isinstance(chunk_id, str):
                seen.add(chunk_id)
        assessment["supporting_chunk_ids"] = unique_ids
    return canonical, duplicate_count


def validate_entailment_analysis(
    requirement_analysis: A1RequirementAnalysis,
    entailment_analysis: A1EntailmentAnalysis,
    candidate_chunk_ids: list[str],
) -> None:
    """Validate dynamic identities that JSON Schema cannot fully express."""

    expected_ids = [row.requirement_id for row in requirement_analysis.requirements]
    actual_ids = [row.requirement_id for row in entailment_analysis.assessments]
    if len(actual_ids) != len(set(actual_ids)) or set(actual_ids) != set(expected_ids):
        raise ValueError("Stage 2 must assess each Stage 1 requirement exactly once")
    allowed = set(candidate_chunk_ids)
    for assessment in entailment_analysis.assessments:
        outside_ids = set(assessment.supporting_chunk_ids) - allowed
        if outside_ids:
            raise ValueError(
                "Stage 2 returned chunk IDs outside Dense Top 3: "
                + ", ".join(sorted(outside_ids))
            )


def reduce_a1_decision(
    requirement_analysis: A1RequirementAnalysis,
    entailment_analysis: A1EntailmentAnalysis,
    candidate_chunk_ids: list[str],
) -> ReviewerDecision:
    """Apply the frozen all-requirements-supported policy in deterministic code."""

    validate_entailment_analysis(
        requirement_analysis, entailment_analysis, candidate_chunk_ids
    )
    assessments_by_id = {
        row.requirement_id: row for row in entailment_analysis.assessments
    }
    unsupported = [
        row.requirement_id
        for row in requirement_analysis.requirements
        if not assessments_by_id[row.requirement_id].supported
    ]
    if unsupported:
        return ReviewerDecision(
            decision="reject",
            decision_reason="Unsupported essential requirements: " + ", ".join(unsupported),
            supporting_chunk_ids=[],
        )

    selected = {
        chunk_id
        for assessment in entailment_analysis.assessments
        for chunk_id in assessment.supporting_chunk_ids
    }
    ordered_ids = [chunk_id for chunk_id in candidate_chunk_ids if chunk_id in selected]
    return ReviewerDecision(
        decision="accept",
        decision_reason=(
            f"All {len(requirement_analysis.requirements)} essential requirements "
            "are directly supported."
        ),
        supporting_chunk_ids=ordered_ids,
    )
