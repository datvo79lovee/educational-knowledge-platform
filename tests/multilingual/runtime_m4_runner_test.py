"""Contract tests for the M4 runtime-failure-rate runner.

M4 must observe the runtime without changing it, keep diagnostics on the error path,
and continue past a failure. These tests exercise those properties without loading the
encoder and without calling Ollama.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

import scripts.evaluation.run_multilingual_runtime_v1_m4 as runner
from scripts.evaluation.run_multilingual_runtime_v1_m4 import (
    FAILURE_LAYERS,
    PROJECT_ROOT,
    RESULT_ARTIFACT_NAMES,
    RecordingGenerationProvider,
    RecordingSearchService,
    RecordingTranslator,
    classify_failure,
    extract_raw_model_output,
    summarise,
)
from src.grounded_answer.contracts import ModelGroundedDecision
from src.grounded_answer.ollama_provider import GroundedAnswerProviderError
from src.grounded_answer.provider import GenerationProviderResult
from src.grounded_answer.service import GroundedAnswerContractError, GroundedAnswerService
from src.multilingual.translation import (
    TranslationContractError,
    TranslationError,
    TranslationProviderError,
    TranslationResult,
)

M3_PREREGISTRATION = PROJECT_ROOT / "reports/31_multilingual_runtime_v1_m3/m3_preregistration.json"
M4_PREREGISTRATION = PROJECT_ROOT / "reports/32_multilingual_runtime_v1_m4/m4_preregistration.json"
REPORT_DIR = PROJECT_ROOT / "reports/32_multilingual_runtime_v1_m4"


class _InnerTranslator:
    def __init__(self, result: object) -> None:
        self.result = result
        self.seen: list[str] = []

    def translate(self, question_vi: str) -> object:
        self.seen.append(question_vi)
        return self.result


class _InnerSearch:
    def __init__(self, results: list[dict[str, object]]) -> None:
        self.results = results
        self.seen: list[str] = []
        self.index_run_id = "index-run-id"

    def search(self, query: str) -> list[dict[str, object]]:
        self.seen.append(query)
        return self.results


def test_recording_translator_is_pure_delegation() -> None:
    sentinel = object()
    inner = _InnerTranslator(sentinel)
    wrapper = RecordingTranslator(inner)

    returned = wrapper.translate("câu hỏi")

    assert returned is sentinel, "wrapper must return the inner result unchanged"
    assert inner.seen == ["câu hỏi"], "wrapper must not alter the question"
    assert wrapper.last_result is sentinel
    assert wrapper.call_count == 1
    wrapper.reset()
    assert wrapper.last_result is None and wrapper.call_count == 0


def test_recording_search_service_is_pure_delegation() -> None:
    results = [{"chunk_id": "c1", "rank": 1}]
    inner = _InnerSearch(results)
    wrapper = RecordingSearchService(inner)

    returned = wrapper.search("Learning Objectives")

    assert returned is results, "wrapper must return the inner result unchanged"
    assert inner.seen == ["Learning Objectives"]
    assert wrapper.index_run_id == "index-run-id", "index_run_id must proxy to the inner service"
    assert wrapper.last_results is results
    assert wrapper.call_count == 1


@pytest.mark.parametrize(
    ("error", "expected_layer"),
    [
        (TranslationContractError("x"), "translation_contract"),
        (TranslationProviderError("x"), "translation_provider"),
        (TranslationError("x"), "translation_other"),
        (GroundedAnswerContractError("x"), "generation_contract"),
        (GroundedAnswerProviderError("x"), "generation_provider"),
        (RuntimeError("x"), "runtime_other"),
    ],
)
def test_failure_layers_are_assigned_by_declared_rule(error: Exception, expected_layer: str) -> None:
    assert classify_failure(error) == expected_layer
    assert expected_layer in FAILURE_LAYERS


def test_raw_generator_payload_survives_a_contract_failure() -> None:
    """The string form of a pydantic error truncates; the structured form does not."""

    payload = {
        "decision": "abstain",
        "answer": "Một câu trả lời tiếng Việt đủ dài để bị cắt trong thông điệp lỗi mặc định của pydantic",
        "supporting_chunk_ids": [],
        "reason": "lý do",
    }
    try:
        ModelGroundedDecision.model_validate(payload)
    except ValidationError as validation_error:
        # Python clears the exception name when the except block ends, so keep what is needed.
        default_message = str(validation_error)
        wrapped = GroundedAnswerContractError("strict validation failed")
        wrapped.__cause__ = validation_error
        captured = extract_raw_model_output(wrapped)
    else:  # pragma: no cover - the payload is invalid by construction
        pytest.fail("payload should not validate")

    assert captured is not None
    assert captured["capture"] == "validation_error_input"
    assert captured["payload"] == payload
    assert "..." in default_message, "the default message is the truncated one"
    assert payload["answer"] not in default_message, "the full answer is not in the default message"


def test_raw_text_survives_a_json_decode_failure() -> None:
    broken = '{"decision": "answer", broken'
    try:
        json.loads(broken)
    except json.JSONDecodeError as decode_error:
        wrapped = GroundedAnswerContractError("strict validation failed")
        wrapped.__cause__ = decode_error
        captured = extract_raw_model_output(wrapped)
    else:  # pragma: no cover - the text is invalid by construction
        pytest.fail("text should not parse")

    assert captured == {"capture": "json_decode_error_doc", "payload": broken}


def test_summary_counts_failures_by_layer_with_intervals() -> None:
    records = [
        {"intent_id": "a", "runtime_status": "passed", "failure_layer": None, "decision": "answer",
         "raw_model_output": {"capture": "execution_raw_output"}, "retrieval_query": "q", "top3_chunk_ids": ["c"]},
        {"intent_id": "b", "runtime_status": "passed", "failure_layer": None, "decision": "abstain",
         "raw_model_output": {"capture": "execution_raw_output"}, "retrieval_query": "q", "top3_chunk_ids": ["c"]},
        {"intent_id": "c", "runtime_status": "failed", "failure_layer": "generation_contract", "decision": None,
         "raw_model_output": {"capture": "validation_error_input"}, "retrieval_query": "q", "top3_chunk_ids": ["c"]},
        {"intent_id": "d", "runtime_status": "failed", "failure_layer": "translation_contract", "decision": None,
         "raw_model_output": None, "retrieval_query": None, "top3_chunk_ids": []},
    ]

    summary = summarise(records)

    assert summary["executed_intent_count"] == 4
    assert summary["passed_count"] == 2 and summary["failed_count"] == 2
    assert summary["runtime_failure_rate"]["rate"] == 0.5
    low, high = summary["runtime_failure_rate"]["wilson_95"]
    assert 0.0 < low < 0.5 < high < 1.0
    assert summary["failure_layer_counts"]["generation_contract"] == 1
    assert summary["failure_layer_counts"]["translation_contract"] == 1
    assert summary["failed_intent_ids"] == ["c", "d"]
    assert summary["raw_model_output_captured_on_failure"] == 1
    assert summary["retrieval_query_captured_on_failure"] == 1
    assert summary["decision_counts_among_passed"] == {"answer": 1, "abstain": 1}
    assert summary["quality_metrics_computed"] is False


def test_preregistration_pins_the_same_runtime_as_m3() -> None:
    """M4 must measure the runtime M3 attempted, byte for byte."""

    m3 = json.loads(M3_PREREGISTRATION.read_text(encoding="utf-8"))
    m4 = json.loads(M4_PREREGISTRATION.read_text(encoding="utf-8"))

    assert (
        m4["runtime_under_test"]["source_sha256_lf_normalized"]
        == m3["runtime_under_test"]["source_sha256_lf_normalized"]
    )
    assert m4["runtime_unchanged_since_m3"]["verified"] is True
    assert m4["instrument_change"]["continue_after_failure"] is True
    assert m4["instrument_change"]["retry_count"] == 0
    assert m4["no_promotion_gate"]["declared"] is True


def _result_artifact_state() -> dict[str, str | None]:
    state: dict[str, str | None] = {}
    for name in RESULT_ARTIFACT_NAMES:
        path = REPORT_DIR / name
        state[name] = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    return state


def test_frozen_m4_verify_only_refuses_runtime_drift_without_touching_artifacts() -> None:
    script = PROJECT_ROOT / "scripts/evaluation/run_multilingual_runtime_v1_m4.py"
    before = _result_artifact_state()
    completed = subprocess.run(
        [sys.executable, "-X", "utf8", str(script), "--verify-only"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert completed.returncode != 0
    assert "Runtime under test changed since pre-registration" in completed.stderr
    assert "src/grounded_answer/service.py" in completed.stderr
    assert _result_artifact_state() == before


def test_runner_refuses_to_overwrite_existing_results(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(runner, "REPORT_DIR", tmp_path)
    (tmp_path / RESULT_ARTIFACT_NAMES[0]).write_text("{}", encoding="utf-8")

    with pytest.raises(FileExistsError):
        runner.ensure_no_existing_result_artifacts()


# --- Revision 2 hardening: the three invariants revision 1 promised but did not enforce ---


def _candidate(rank: int, chunk_id: str) -> dict[str, object]:
    return {
        "rank": rank,
        "chunk_id": chunk_id,
        "chunk_text": f"excerpt {rank}",
        "score": 0.5 - rank * 0.01,
        "video_id": "vid",
        "video_title": "title",
        "start_second": 10.0 * rank,
        "end_second": 10.0 * rank + 5.0,
        "source_url": "https://www.youtube.com/watch?v=vid",
        "citation_url": f"https://www.youtube.com/watch?v=vid&t={10 * rank}s",
    }


class _StubTranslatorInner:
    def translate(self, question_vi: str) -> TranslationResult:
        return TranslationResult(literal_en="Learning Objectives", prompt_eval_count=82, eval_count=6)


class _StubSearchInner:
    index_run_id = "stub-index-run"

    def search(self, query: str) -> list[dict[str, object]]:
        return [_candidate(1, "c1"), _candidate(2, "c2"), _candidate(3, "c3")]


class _StubGeneratorInner:
    """Returns a payload that the strict contract rejects: abstain with an answer."""

    def __init__(self, content: str) -> None:
        self.content = content

    def verify_runtime(self) -> dict[str, object]:
        return {"model": "stub"}

    def generate(self, *, system_prompt: str, user_prompt: str, output_schema: dict[str, object]):
        return GenerationProviderResult(content=self.content, prompt_eval_count=757, eval_count=145)


def _wired_service(content: str):
    translator = RecordingTranslator(_StubTranslatorInner())
    search = RecordingSearchService(_StubSearchInner())
    generator = RecordingGenerationProvider(_StubGeneratorInner(content))
    service = GroundedAnswerService(search_service=search, provider=generator, translator=translator)
    return service, translator, search, generator


def test_failed_record_keeps_every_promised_diagnostic() -> None:
    """The M3 q-002 failure mode must now leave a fully diagnosable record."""

    offending = json.dumps(
        {
            "decision": "abstain",
            "answer": "Không đủ bằng chứng, nhưng đây vẫn là một câu trả lời",
            "supporting_chunk_ids": ["outside-top3"],
            "reason": "lý do",
        },
        ensure_ascii=False,
    )
    service, translator, search, generator = _wired_service(offending)

    record = runner.execute_intent(
        service, translator, search, generator, {"intent_id": "stub-1", "question_vi": "câu hỏi"}
    )

    assert record["runtime_status"] == "failed"
    assert record["failure_layer"] == "generation_contract"
    # What M3 attempt 1 lost:
    assert record["retrieval_query"] == "Learning Objectives"
    assert record["top3_chunk_ids"] == ["c1", "c2", "c3"]
    assert record["raw_model_output"]["capture"] == "generation_provider_recorder"
    assert record["raw_model_output"]["parsed"]["answer"].startswith("Không đủ bằng chứng")
    # Declared per-stage metrics, present on the failure path:
    assert record["generation_prompt_eval_count"] == 757
    assert record["generation_eval_count"] == 145
    assert record["translation_prompt_eval_count"] == 82
    for field in ("translation_latency_ms", "retrieval_latency_ms", "generation_latency_ms", "total_latency_ms"):
        assert isinstance(record[field], float)


def test_partial_output_survives_an_interruption(tmp_path: Path) -> None:
    """An interruption at intent 3 must leave the first two records on disk."""

    valid = json.dumps(
        {"decision": "abstain", "answer": None, "supporting_chunk_ids": [], "reason": "r"}, ensure_ascii=False
    )
    service, translator, search, generator = _wired_service(valid)
    outputs = tmp_path / "m4_runtime_outputs.jsonl"

    class _Interrupt(BaseException):
        """Not an Exception, so execute_intent cannot swallow it."""

    intents = [{"intent_id": f"stub-{i}", "question_vi": "câu hỏi"} for i in range(1, 4)]

    # The wrapper resets its counter per intent, so count invocations independently.
    invocations = {"count": 0}

    def exploding_search(query: str) -> list[dict[str, object]]:
        invocations["count"] += 1
        if invocations["count"] >= 3:
            raise _Interrupt("machine interrupted")
        return [_candidate(1, "c1"), _candidate(2, "c2"), _candidate(3, "c3")]

    search.inner.search = exploding_search  # type: ignore[method-assign]

    with pytest.raises(_Interrupt):
        runner.run_execution(service, translator, search, generator, intents, outputs, announce=False)

    written = [json.loads(line) for line in outputs.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert [row["intent_id"] for row in written] == ["stub-1", "stub-2"]


def test_integrity_conditions_fail_when_runtime_changed_after_execution() -> None:
    records = [
        {
            "intent_id": "a",
            "runtime_status": "passed",
            "failure_layer": None,
            "error_type": None,
            "raw_model_output": {"capture": "generation_provider_recorder"},
            "translation_call_count": 1,
            "retrieval_call_count": 1,
            "generation_call_count": 1,
        }
    ]

    clean = runner.evaluate_integrity_conditions(records, [], expected_intent_count=1)
    assert clean["conditions"]["I4"]["result"] == "PASS"
    assert clean["all_passed"] is True

    tampered = runner.evaluate_integrity_conditions(
        records, ["src/grounded_answer/prompts.py"], expected_intent_count=1
    )
    assert tampered["conditions"]["I4"]["result"] == "FAIL"
    assert tampered["conditions"]["I4"]["mismatched_sources"] == ["src/grounded_answer/prompts.py"]
    assert tampered["all_passed"] is False


def test_runtime_source_mismatch_detection_is_real() -> None:
    prereg = json.loads(M4_PREREGISTRATION.read_text(encoding="utf-8"))
    assert runner.runtime_source_mismatches(prereg) == ["src/grounded_answer/service.py"]

    tampered = json.loads(M4_PREREGISTRATION.read_text(encoding="utf-8"))
    first = next(iter(tampered["runtime_under_test"]["source_sha256_lf_normalized"]))
    tampered["runtime_under_test"]["source_sha256_lf_normalized"][first] = "0" * 64
    assert set(runner.runtime_source_mismatches(tampered)) == {first, "src/grounded_answer/service.py"}


def test_integrity_conditions_fail_when_a_failed_record_lost_its_payload() -> None:
    records = [
        {
            "intent_id": "a",
            "runtime_status": "failed",
            "failure_layer": "generation_contract",
            "error_type": "GroundedAnswerContractError",
            "raw_model_output": None,
            "translation_call_count": 1,
            "retrieval_call_count": 1,
            "generation_call_count": 1,
        }
    ]

    result = runner.evaluate_integrity_conditions(records, [], expected_intent_count=1)
    assert result["conditions"]["I3"]["result"] == "FAIL"


# --- Revision 3: the analysis layer is pinned AND verified ---


def test_analysis_code_pins_cover_both_runners() -> None:
    prereg = json.loads(M4_PREREGISTRATION.read_text(encoding="utf-8"))
    pinned = prereg["analysis_code_sha256_lf_normalized"]

    assert set(pinned) == {
        "scripts/evaluation/run_multilingual_runtime_v1_m4.py",
        "scripts/evaluation/run_multilingual_runtime_v1_m3.py",
    }, "the M3 runner is imported for the Wilson interval, so it is analysis code too"
    assert runner.analysis_code_mismatches(prereg) == []
    assert prereg["analysis_code_verification"]["verified_before_any_model_call"] is True


def test_analysis_code_mismatch_is_detected() -> None:
    tampered = json.loads(M4_PREREGISTRATION.read_text(encoding="utf-8"))
    target = "scripts/evaluation/run_multilingual_runtime_v1_m3.py"
    tampered["analysis_code_sha256_lf_normalized"][target] = "0" * 64

    assert runner.analysis_code_mismatches(tampered) == [target]
    with pytest.raises(ValueError, match="Analysis code changed since pre-registration"):
        runner.verify_analysis_code(tampered)


def test_runner_refuses_to_start_when_analysis_hash_is_wrong(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A wrong analysis hash must stop the run before the encoder and before Ollama."""

    tampered = json.loads(M4_PREREGISTRATION.read_text(encoding="utf-8"))
    tampered["runtime_under_test"]["source_sha256_lf_normalized"] = {
        relative_path: runner.sha256_file_lf(PROJECT_ROOT / relative_path)
        for relative_path in tampered["runtime_under_test"]["source_sha256_lf_normalized"]
    }
    tampered["analysis_code_sha256_lf_normalized"][
        "scripts/evaluation/run_multilingual_runtime_v1_m4.py"
    ] = "0" * 64
    tampered_path = tmp_path / "m4_preregistration.json"
    tampered_path.write_text(json.dumps(tampered, ensure_ascii=False), encoding="utf-8")

    monkeypatch.setattr(runner, "PREREGISTRATION", tampered_path)
    monkeypatch.setattr(sys, "argv", ["run_multilingual_runtime_v1_m4.py", "--verify-only"])

    with pytest.raises(ValueError, match="Analysis code changed since pre-registration"):
        runner.main()

    # The refusal happens before anything can be written.
    assert not any((tmp_path / name).exists() for name in RESULT_ARTIFACT_NAMES)


def test_analysis_verification_runs_before_the_execution_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ordering matters: a bad analysis hash must not be reported as a stale-artifact error."""

    calls: list[str] = []
    monkeypatch.setattr(runner, "verify_frozen_inputs", lambda prereg: calls.append("frozen"))
    monkeypatch.setattr(runner, "verify_runtime_sources", lambda prereg: calls.append("runtime"))
    monkeypatch.setattr(runner, "verify_analysis_code", lambda prereg: calls.append("analysis"))
    monkeypatch.setattr(
        runner, "ensure_no_existing_result_artifacts", lambda: calls.append("artifact_guard")
    )
    monkeypatch.setattr(sys, "argv", ["run_multilingual_runtime_v1_m4.py", "--verify-only"])

    runner.main()

    assert calls == ["frozen", "runtime", "analysis"], "verify-only must stop before the artifact guard"
