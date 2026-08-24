"""M2 contract/runtime tests không gọi model và không đọc evaluation labels."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any

import pytest
from fastapi import HTTPException
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from src.grounded_answer.contracts import (
    GroundedAnswerRequest,
    ModelGroundedDecision,
    build_model_output_schema,
)
from src.grounded_answer.ollama_provider import OllamaGroundedGenerationProvider
from src.grounded_answer.provider import GenerationProviderResult
from src.grounded_answer.service import (
    normalize_model_output,
    GroundedAnswerContractError,
    GroundedAnswerService,
)
from src.grounded_answer.prompts import SYSTEM_PROMPT
from src.multilingual.translation import (
    TranslationContractError,
    TranslationError,
    TranslationProviderError,
    TranslationResult,
)
from src.search_api.app import answer as answer_endpoint


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def candidate(rank: int) -> dict[str, Any]:
    return {
        "rank": rank,
        "chunk_id": f"chunk-{rank}",
        "chunk_text": f"Transcript excerpt {rank}",
        "score": 1.0 / rank,
        "video_id": f"video-{rank}",
        "video_title": f"Video {rank}",
        "start_second": float(rank * 10),
        "end_second": float(rank * 10 + 5),
        "source_url": f"https://www.youtube.com/watch?v=video-{rank}",
        "citation_url": f"https://www.youtube.com/watch?v=video-{rank}&t={rank * 10}s",
    }


class FakeSearchService:
    index_run_id = "index-test"

    def __init__(self) -> None:
        self.call_count = 0

    def search(self, question: str) -> list[dict[str, Any]]:
        self.call_count += 1
        assert question
        return [candidate(rank) for rank in (1, 2, 3)]


class FakeProvider:
    def __init__(self, payload: dict[str, Any] | str) -> None:
        self.payload = payload
        self.call_count = 0
        self.last_schema: dict[str, Any] | None = None
        self.last_user_prompt: str | None = None

    def verify_runtime(self) -> dict[str, Any]:
        return {"status": "fake"}

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
    ) -> GenerationProviderResult:
        self.call_count += 1
        assert system_prompt
        assert "Candidate excerpts" in user_prompt
        self.last_schema = output_schema
        self.last_user_prompt = user_prompt
        content = self.payload if isinstance(self.payload, str) else json.dumps(self.payload)
        return GenerationProviderResult(
            content=content,
            prompt_eval_count=10,
            eval_count=5,
        )


def build_service(payload: dict[str, Any] | str) -> tuple[GroundedAnswerService, FakeSearchService, FakeProvider]:
    search = FakeSearchService()
    provider = FakeProvider(payload)
    service = GroundedAnswerService(search_service=search, provider=provider)  # type: ignore[arg-type]
    return service, search, provider


class FakeTranslator:
    def __init__(self, literal_en: str) -> None:
        self.literal_en = literal_en
        self.call_count = 0
        self.received: str | None = None

    def translate(self, question_vi: str) -> TranslationResult:
        self.call_count += 1
        self.received = question_vi
        return TranslationResult(
            literal_en=self.literal_en,
            prompt_eval_count=4,
            eval_count=3,
        )


def test_request_rejects_client_supplied_evidence() -> None:
    assert GroundedAnswerRequest(question="  What is a list?  ").question == "What is a list?"
    with pytest.raises(ValidationError):
        GroundedAnswerRequest(question=" ")
    with pytest.raises(ValidationError):
        GroundedAnswerRequest(question="What is a list?", candidates=[])


def test_answer_maps_citations_in_retrieval_rank_order_with_one_model_call() -> None:
    service, search, provider = build_service(
        {
            "decision": "answer",
            "answer": "A grounded answer.",
            "supporting_chunk_ids": ["chunk-3", "chunk-1"],
            "reason": "Chunks 1 and 3 support the answer.",
        }
    )
    execution = service.answer("Question")

    assert search.call_count == 1
    assert provider.call_count == 1
    assert execution.response.supporting_chunk_ids == ["chunk-1", "chunk-3"]
    assert [row.chunk_id for row in execution.response.citations] == ["chunk-1", "chunk-3"]
    assert execution.response.citations[0].video_url == candidate(1)["source_url"]
    assert execution.response.citations[0].start == candidate(1)["start_second"]
    assert execution.response.citations[0].end == candidate(1)["end_second"]
    assert execution.response.citations[0].citation_url == candidate(1)["citation_url"]
    assert execution.reason not in execution.response.model_dump()
    assert provider.last_schema is not None
    schema_text = json.dumps(provider.last_schema)
    assert "chunk-1" in schema_text and "chunk-3" in schema_text


def test_abstain_has_no_answer_evidence_or_citations() -> None:
    service, _, provider = build_service(
        {
            "decision": "abstain",
            "answer": None,
            "supporting_chunk_ids": [],
            "reason": "The excerpts are insufficient.",
        }
    )
    response = service.answer("Question").response

    assert provider.call_count == 1
    assert response.answer is None
    assert response.supporting_chunk_ids == []
    assert response.citations == []


def test_vietnamese_branch_translates_only_original_query_then_retrieves_literal_english() -> None:
    search = FakeSearchService()
    provider = FakeProvider(
        {
            "decision": "answer",
            "answer": "Câu trả lời có căn cứ.",
            "supporting_chunk_ids": ["chunk-1"],
            "reason": "Evidence supports the answer.",
        }
    )
    translator = FakeTranslator("Why does a recursive function need a base case?")
    service = GroundedAnswerService(
        search_service=search,
        provider=provider,  # type: ignore[arg-type]
        translator=translator,
    )

    response = service.answer(" Vì sao hàm đệ quy cần base case? ", "vi").response

    assert translator.call_count == 1
    assert translator.received == "Vì sao hàm đệ quy cần base case?"
    assert search.call_count == 1
    assert response.original_query == "Vì sao hàm đệ quy cần base case?"
    assert response.retrieval_query == "Why does a recursive function need a base case?"
    assert response.answer_language == "vi"
    assert service.answer("Vì sao hàm đệ quy cần base case?", "vi").translation_call_count == 1
    assert provider.last_user_prompt is not None
    assert "Answer language: vi" in provider.last_user_prompt


def test_english_branch_does_not_require_or_call_translator() -> None:
    service, _, _ = build_service(
        {
            "decision": "abstain",
            "answer": None,
            "supporting_chunk_ids": [],
            "reason": "The excerpts are insufficient.",
        }
    )

    response = service.answer("What is recursion?", "en").response

    assert response.original_query == "What is recursion?"
    assert response.retrieval_query == "What is recursion?"
    assert response.answer_language == "en"


def test_missing_vietnamese_translator_fails_closed() -> None:
    service, search, provider = build_service(
        {
            "decision": "abstain",
            "answer": None,
            "supporting_chunk_ids": [],
            "reason": "The excerpts are insufficient.",
        }
    )
    with pytest.raises(TranslationError):
        service.answer("Câu hỏi tiếng Việt", "vi")
    assert search.call_count == 0
    assert provider.call_count == 0


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (TranslationContractError("bad translation"), 502),
        (TranslationProviderError("translator unavailable"), 503),
    ],
)
def test_translation_errors_have_stable_http_mapping(
    error: TranslationError,
    expected_status: int,
) -> None:
    class FailingService:
        def answer(self, question: str, answer_language: str) -> Any:
            raise error

    with pytest.raises(HTTPException) as caught:
        answer_endpoint(
            GroundedAnswerRequest(question="Câu hỏi", answer_language="vi"),
            FailingService(),  # type: ignore[arg-type]
        )
    assert caught.value.status_code == expected_status


def test_english_prompt_v1_hash_is_frozen() -> None:
    assert hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest() == (
        "2b0a35d600e1497c53b62e3d311b0f63802fb1dc0518cdb0dd57b67cd712f459"
    )


def test_abstain_literal_is_normalized_and_audited() -> None:
    service, _, _ = build_service(
        {
            "decision": "abstain",
            "answer": "abstain",
            "supporting_chunk_ids": [],
            "reason": "The excerpts are insufficient.",
        }
    )
    execution = service.answer("Question")

    assert execution.response.decision == "abstain"
    assert execution.response.answer is None
    assert execution.response.supporting_chunk_ids == []
    assert execution.raw_model_output["answer"] == "abstain"
    assert execution.normalized_output["answer"] is None
    assert execution.normalization_applied is True
    assert execution.normalization_reason == "abstain_literal_to_null"
    assert "raw_model_output" not in execution.response.model_dump()


def test_duplicate_supporting_ids_are_stably_normalized_and_audited() -> None:
    service, _, _ = build_service(
        {
            "decision": "answer",
            "answer": "A grounded answer.",
            "supporting_chunk_ids": ["chunk-3", "chunk-1", "chunk-3"],
            "reason": "Chunks 1 and 3 support the answer.",
        }
    )
    execution = service.answer("Question")

    assert execution.response.supporting_chunk_ids == ["chunk-1", "chunk-3"]
    assert execution.raw_model_output["supporting_chunk_ids"] == [
        "chunk-3",
        "chunk-1",
        "chunk-3",
    ]
    assert execution.normalized_output["supporting_chunk_ids"] == ["chunk-3", "chunk-1"]
    assert execution.normalization_applied is True
    assert execution.normalization_reason == "duplicate_supporting_ids"
    assert [row.chunk_id for row in execution.response.citations] == ["chunk-1", "chunk-3"]


@pytest.mark.parametrize(
    "payload",
    [
        {
            "decision": "answer",
            "answer": "Unsupported.",
            "supporting_chunk_ids": ["outside-id"],
            "reason": "Invalid ID.",
        },
        {
            "decision": "answer",
            "answer": "Unknown duplicate.",
            "supporting_chunk_ids": ["outside-id", "outside-id"],
            "reason": "Unknown IDs must not be normalized.",
        },
        {
            "decision": "answer",
            "answer": "",
            "supporting_chunk_ids": ["chunk-1", "chunk-1"],
            "reason": "Empty answers must not be normalized.",
        },
        "not valid json",
        {
            "decision": "answer",
            "answer": "No support.",
            "supporting_chunk_ids": [],
            "reason": "No IDs.",
        },
        {
            "decision": "abstain",
            "answer": "Should be null.",
            "supporting_chunk_ids": [],
            "reason": "Invalid abstain answer.",
        },
        {
            "decision": "abstain",
            "answer": None,
            "supporting_chunk_ids": ["chunk-1"],
            "reason": "Invalid abstain evidence.",
        },
    ],
)
def test_invalid_model_outputs_fail_without_repair(payload: dict[str, Any] | str) -> None:
    service, _, provider = build_service(payload)
    with pytest.raises(GroundedAnswerContractError):
        service.answer("Question")
    assert provider.call_count == 1


@pytest.mark.parametrize(
    "payload",
    [
        {
            "decision": "answer",
            "answer": "Answer.",
            "supporting_chunk_ids": ["outside-id", "outside-id"],
            "reason": "Unknown IDs.",
        },
        {
            "decision": "answer",
            "answer": "",
            "supporting_chunk_ids": ["chunk-1", "chunk-1"],
            "reason": "Empty answer.",
        },
        {
            "decision": "abstain",
            "answer": "abstain",
            "supporting_chunk_ids": ["chunk-1"],
            "reason": "Abstain with evidence.",
        },
        {
            "decision": "abstain",
            "answer": "Should be null.",
            "supporting_chunk_ids": [],
            "reason": "Different contradiction.",
        },
        "not valid json",
    ],
)
def test_normalizer_refuses_out_of_scope_repairs(payload: Any) -> None:
    audit = normalize_model_output(payload, ["chunk-1", "chunk-2", "chunk-3"])

    assert audit.normalization_applied is False
    assert audit.normalization_reason is None
    assert audit.normalized_output == audit.raw_model_output


def test_static_and_dynamic_schemas_are_valid() -> None:
    for relative_path in (
        "schemas/grounded_answer_model_output_v1.schema.json",
        "schemas/grounded_answer_api_v1.schema.json",
        "schemas/grounded_answer_runtime_manifest_v1.schema.json",
    ):
        schema = json.loads((PROJECT_ROOT / relative_path).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)

    dynamic = build_model_output_schema(["chunk-1", "chunk-2", "chunk-3"])
    Draft202012Validator.check_schema(dynamic)


def test_static_and_dynamic_schemas_enforce_abstain_shape() -> None:
    static = json.loads(
        (PROJECT_ROOT / "schemas/grounded_answer_model_output_v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    dynamic = build_model_output_schema(["chunk-1", "chunk-2", "chunk-3"])
    valid_abstain = {
        "decision": "abstain",
        "answer": None,
        "supporting_chunk_ids": [],
        "reason": "The excerpts are insufficient.",
    }
    invalid_abstain_answer = {**valid_abstain, "answer": "abstain"}
    invalid_abstain_evidence = {**valid_abstain, "supporting_chunk_ids": ["chunk-1"]}

    for schema in (static, dynamic):
        validator = Draft202012Validator(schema)
        validator.validate(valid_abstain)
        assert list(validator.iter_errors(invalid_abstain_answer))
        assert list(validator.iter_errors(invalid_abstain_evidence))


def test_model_contract_rejects_empty_answer_and_duplicate_ids() -> None:
    with pytest.raises(ValidationError):
        ModelGroundedDecision(
            decision="answer",
            answer=" ",
            supporting_chunk_ids=["chunk-1"],
            reason="reason",
        )
    with pytest.raises(ValidationError):
        ModelGroundedDecision(
            decision="answer",
            answer="answer",
            supporting_chunk_ids=["chunk-1", "chunk-1"],
            reason="reason",
        )


def test_active_runtime_has_no_evaluation_label_access() -> None:
    prohibited = (
        "expected_answer_points",
        "relevant_time_ranges",
        "human_label",
        "evaluation_questions.jsonl",
        "evidence_accept_reject",
    )
    active_files = (
        list((PROJECT_ROOT / "src/grounded_answer").glob("*.py"))
        + list((PROJECT_ROOT / "src/multilingual").glob("*.py"))
        + [PROJECT_ROOT / "src/search_api/app.py"]
    )
    for path in active_files:
        content = path.read_text(encoding="utf-8")
        assert not any(value in content for value in prohibited), path


def test_frozen_runtime_manifest_and_output_hashes() -> None:
    report_root = PROJECT_ROOT / "reports/20_grounded_answer_runtime"
    manifest = json.loads(
        (report_root / "grounded_answer_runtime_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    schema = json.loads(
        (
            PROJECT_ROOT / "schemas/grounded_answer_runtime_manifest_v1.schema.json"
        ).read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(manifest)
    assert manifest["validation_status"] == "passed"
    assert manifest["implementation_status"] == (
        "complete_runtime_only_not_quality_evaluated"
    )
    assert manifest["smoke"]["model_call_count"] == 2
    assert manifest["smoke"]["answer_count"] == 1
    assert manifest["smoke"]["abstain_count"] == 1
    assert manifest["contracts"]["auto_repair_used"] is False
    for artifact in manifest["output_artifacts"]:
        path = PROJECT_ROOT / artifact["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"]


def test_ollama_provider_verifies_digest_lazily_before_chat() -> None:
    provider = OllamaGroundedGenerationProvider(
        endpoint="http://local",
        model="llama3.2:3b",
        expected_digest="a" * 64,
        temperature=0,
        seed=42,
        num_predict=512,
        num_ctx=4096,
        timeout_seconds=1,
    )
    paths: list[str] = []

    def fake_request(path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        paths.append(path)
        if path == "/api/version":
            return {"version": "test"}
        if path == "/api/tags":
            return {
                "models": [
                    {
                        "name": "llama3.2:3b",
                        "digest": "a" * 64,
                        "size": 1,
                        "details": {
                            "family": "llama",
                            "parameter_size": "3.2B",
                            "quantization_level": "Q4_K_M",
                        },
                    }
                ]
            }
        assert path == "/api/chat"
        assert payload is not None
        return {
            "message": {
                "content": json.dumps(
                    {
                        "decision": "abstain",
                        "answer": None,
                        "supporting_chunk_ids": [],
                        "reason": "insufficient",
                    }
                )
            }
        }

    provider._request = fake_request  # type: ignore[method-assign]
    provider.generate(system_prompt="system", user_prompt="user", output_schema={})
    provider.generate(system_prompt="system", user_prompt="user", output_schema={})

    assert paths == ["/api/version", "/api/tags", "/api/chat", "/api/chat"]
