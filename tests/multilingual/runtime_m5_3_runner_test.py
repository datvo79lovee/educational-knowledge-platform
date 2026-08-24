"""Protocol tests for the M5.3 Vietnamese abstention canonicalization candidate."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

import scripts.evaluation.run_multilingual_runtime_v1_m5_3 as runner
from scripts.evaluation.run_multilingual_runtime_v1_m5_3 import (
    NEW_NORMALIZATION_REASON,
    PROJECT_ROOT,
    RESULT_ARTIFACT_NAMES,
    evaluate_gates,
    normalization_violations,
    scope_integrity_report,
    summarise,
)

PREREGISTRATION = PROJECT_ROOT / "reports/34_multilingual_runtime_v1_m5_3/m5_3_preregistration.json"
REPORT_DIR = PROJECT_ROOT / "reports/34_multilingual_runtime_v1_m5_3"


def _record(intent_id: str, *, reason: str | None = None) -> dict[str, object]:
    raw = {
        "decision": "answer",
        "answer": "Một câu trả lời.",
        "supporting_chunk_ids": ["c1"],
        "reason": None,
    }
    normalized = dict(raw)
    decision = "answer"
    answer: str | None = "Một câu trả lời."
    support = ["c1"]
    citations: list[dict[str, object]] = [{"chunk_id": "c1"}]
    if reason == NEW_NORMALIZATION_REASON:
        raw = {
            "decision": "abstain",
            "answer": "Không đủ bằng chứng.",
            "supporting_chunk_ids": [],
            "reason": "Insufficient evidence.",
        }
        normalized = {**raw, "answer": None, "supporting_chunk_ids": []}
        decision = "abstain"
        answer = None
        support = []
        citations = []
    return {
        "intent_id": intent_id,
        "runtime_status": "passed",
        "failure_layer": None,
        "raw_model_output": {"capture": "generation_provider_recorder", "parsed": raw},
        "normalized_output": normalized,
        "decision": decision,
        "answer": answer,
        "supporting_chunk_ids": support,
        "citations": citations,
        "normalization_reason": reason,
        "normalization_applied": reason is not None,
        "retrieval_query": "question",
        "top3_chunk_ids": ["c1", "c2", "c3"],
        "translation_call_count": 1,
        "retrieval_call_count": 1,
        "generation_call_count": 1,
        "translation_latency_ms": 1.0,
        "retrieval_latency_ms": 1.0,
        "generation_latency_ms": 1.0,
        "total_latency_ms": 3.0,
        "generation_prompt_eval_count": 700,
        "generation_eval_count": 20,
    }


def _failed_record(intent_id: str, layer: str) -> dict[str, object]:
    record = _record(intent_id)
    record.update(
        {
            "runtime_status": "failed",
            "failure_layer": layer,
            "error_type": "SomeError",
            "decision": None,
            "answer": None,
            "supporting_chunk_ids": [],
            "citations": [],
        }
    )
    return record


def _artifact_state() -> dict[str, str | None]:
    return {
        name: hashlib.sha256((REPORT_DIR / name).read_bytes()).hexdigest()
        if (REPORT_DIR / name).exists()
        else None
        for name in RESULT_ARTIFACT_NAMES
    }


def test_preregistration_locks_one_vi_only_candidate_and_four_gates() -> None:
    prereg = json.loads(PREREGISTRATION.read_text(encoding="utf-8"))

    assert prereg["status"] == "preregistered_not_executed"
    assert prereg["single_authorized_runtime_change"]["file"] == "src/grounded_answer/service.py"
    assert prereg["single_authorized_runtime_change"]["rule_name"] == NEW_NORMALIZATION_REASON
    assert prereg["scope_integrity"]["authorized_changed_files"] == ["src/grounded_answer/service.py"]
    assert prereg["acceptance_gates"]["pass_rule"] == "G1, G2, G3 and G4 all PASS"
    assert len(prereg["execution_order"]["intent_ids"]) == 20
    assert "English requests" in prereg["single_authorized_runtime_change"]["must_not_normalize"]


def test_current_candidate_matches_runtime_and_symbol_pins() -> None:
    prereg = json.loads(PREREGISTRATION.read_text(encoding="utf-8"))

    assert runner.runtime_source_mismatches(prereg) == []
    assert scope_integrity_report(prereg)["result"] == "PASS"
    symbol_report = runner.runtime_symbol_report(prereg)
    assert symbol_report["result"] == "PASS"
    assert symbol_report["symbols"]["normalize_model_output_source_sha256"]["role"] == "authorized_candidate"
    assert symbol_report["symbols"]["system_prompt_sha256"]["role"] == "frozen"


def test_declared_eligible_payload_is_accepted_only_when_rule_was_applied() -> None:
    clean = _record("a", reason=NEW_NORMALIZATION_REASON)
    missed = dict(clean)
    missed["normalization_reason"] = None
    missed["normalization_applied"] = False

    assert normalization_violations([clean]) == {}
    assert normalization_violations([missed]) == {
        "a": ["eligible_vi_abstain_was_not_canonicalized"]
    }


def test_rule_application_outside_eligibility_is_rejected() -> None:
    record = _record("a", reason=NEW_NORMALIZATION_REASON)
    record["raw_model_output"] = {
        "capture": "generation_provider_recorder",
        "parsed": {
            "decision": "abstain",
            "answer": None,
            "supporting_chunk_ids": ["outside-top3"],
            "reason": "Insufficient evidence.",
        },
    }

    gaps = normalization_violations([record])["a"]

    assert "new_rule_applied_outside_declared_eligibility" in gaps


def test_legacy_literal_null_rule_is_not_misclassified_as_m5_3_eligibility() -> None:
    record = _record("a")
    record.update(
        {
            "raw_model_output": {
                "capture": "generation_provider_recorder",
                "parsed": {
                    "decision": "abstain",
                    "answer": "null",
                    "supporting_chunk_ids": [],
                    "reason": "Insufficient evidence.",
                },
            },
            "normalized_output": {
                "decision": "abstain",
                "answer": None,
                "supporting_chunk_ids": [],
                "reason": "Insufficient evidence.",
            },
            "decision": "abstain",
            "answer": None,
            "supporting_chunk_ids": [],
            "citations": [],
            "normalization_reason": "abstain_literal_to_null",
            "normalization_applied": True,
        }
    )

    assert normalization_violations([record]) == {}


@pytest.mark.parametrize(
    ("field", "value", "expected_gap"),
    [
        ("decision", "answer", "new_rule_without_canonical_abstain_response"),
        ("answer", "leaked", "new_rule_without_canonical_abstain_response"),
        ("supporting_chunk_ids", ["c1"], "new_rule_left_evidence_or_citations"),
        ("citations", [{"chunk_id": "c1"}], "new_rule_left_evidence_or_citations"),
    ],
)
def test_new_rule_must_leave_a_canonical_evidence_free_response(
    field: str, value: object, expected_gap: str
) -> None:
    record = _record("a", reason=NEW_NORMALIZATION_REASON)
    record[field] = value

    assert expected_gap in normalization_violations([record])["a"]


def test_g2_counts_a_failure_from_any_runtime_layer() -> None:
    records = [_record(str(index)) for index in range(19)] + [_failed_record("19", "translation_provider")]
    summary = summarise(records)
    gates = evaluate_gates(records, summary, [], {"result": "PASS"}, [str(index) for index in range(20)])

    assert summary["total_runtime_failure_count"] == 1
    assert gates["conditions"]["G2_runtime_failure"]["result"] == "FAIL"
    assert gates["all_passed"] is False


def test_g1_rejects_balanced_stage_totals_with_per_record_two_plus_zero_calls() -> None:
    records = [_record(str(index)) for index in range(20)]
    records[0]["generation_call_count"] = 2
    records[1]["generation_call_count"] = 0
    summary = summarise(records)

    gates = evaluate_gates(records, summary, [], {"result": "PASS"}, [str(index) for index in range(20)])

    g1 = gates["conditions"]["G1_execution_integrity"]
    assert g1["stage_call_totals"]["generation"] == 20
    assert set(g1["records_with_non_single_stage_calls"]) == {"0", "1"}
    assert g1["result"] == "FAIL"


def test_g4_fails_when_eligible_payload_was_not_canonicalized() -> None:
    records = [_record(str(index)) for index in range(20)]
    records[0] = _record("0", reason=NEW_NORMALIZATION_REASON)
    records[0]["normalization_reason"] = None
    records[0]["normalization_applied"] = False
    summary = summarise(records)

    gates = evaluate_gates(records, summary, [], {"result": "PASS"}, [str(index) for index in range(20)])

    assert gates["conditions"]["G4_normalization_integrity"]["result"] == "FAIL"
    assert gates["all_passed"] is False


@pytest.mark.parametrize(
    ("field", "value", "expected_gap"),
    [
        ("normalization_applied", False, "new_rule_reason_without_applied_audit_flag"),
        (
            "normalized_output",
            {"decision": "answer", "answer": None, "supporting_chunk_ids": []},
            "new_rule_normalized_shape_invalid",
        ),
    ],
)
def test_g4_rejects_incomplete_normalization_audit_or_shape(
    field: str, value: object, expected_gap: str
) -> None:
    record = _record("a", reason=NEW_NORMALIZATION_REASON)
    record[field] = value

    assert expected_gap in normalization_violations([record])["a"]


@pytest.mark.parametrize(
    ("section", "path"),
    [
        ("frozen_inputs_sha256", "data/gold/mit_60001/chunks.jsonl"),
        ("analysis_code_sha256_lf_normalized", "scripts/evaluation/run_multilingual_runtime_v1_m5_3.py"),
    ],
)
def test_hash_mismatch_is_refused(section: str, path: str) -> None:
    prereg = json.loads(PREREGISTRATION.read_text(encoding="utf-8"))
    prereg[section][path] = "0" * 64

    with pytest.raises(ValueError):
        if section == "frozen_inputs_sha256":
            runner.verify_frozen_inputs(prereg)
        else:
            runner.verify_analysis_code(prereg)


def test_verify_only_is_read_only_and_does_not_call_models() -> None:
    before = _artifact_state()
    completed = subprocess.run(
        [sys.executable, "-X", "utf8", str(Path(runner.__file__)), "--verify-only"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert completed.returncode == 0, completed.stderr
    assert "no encoder load and no Ollama call was made" in completed.stdout
    assert _artifact_state() == before


def test_runner_refuses_to_overwrite_a_result_artifact(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(runner, "REPORT_DIR", tmp_path)
    (tmp_path / RESULT_ARTIFACT_NAMES[0]).write_text("existing", encoding="utf-8")

    with pytest.raises(FileExistsError):
        runner.ensure_no_existing_result_artifacts()
