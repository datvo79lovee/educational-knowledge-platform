"""Contract tests for the M5.1 conditional-abstention prompt experiment.

M5.1 changes one prompt artifact comprising exactly two runtime symbols and must prove
it: ``VI_SYSTEM_PROMPT`` is behavioral, while ``VI_PROMPT_VERSION`` carries identity
and provenance only. These tests exercise the scope checks, the corrected gate rule
and the pre-execution hash refusals without loading the encoder or calling Ollama.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import subprocess
import sys
from pathlib import Path

import pytest

import scripts.evaluation.run_multilingual_runtime_v1_m4 as m4_runner
import scripts.evaluation.run_multilingual_runtime_v1_m5 as runner
from scripts.evaluation.run_multilingual_runtime_v1_m5 import (
    PROJECT_ROOT,
    RESULT_ARTIFACT_NAMES,
    diagnostic_gaps,
    evaluate_gates,
    prompt_symbol_report,
    scope_integrity_report,
    summarise,
)
from src.grounded_answer.prompts import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    VI_PROMPT_VERSION,
    VI_SYSTEM_PROMPT,
    build_user_prompt,
)

M5_PREREGISTRATION = PROJECT_ROOT / "reports/33_multilingual_runtime_v1_m5/m5_preregistration.json"
REPORT_DIR = PROJECT_ROOT / "reports/33_multilingual_runtime_v1_m5"
FROZEN_EN_PROMPT_SHA = "2b0a35d600e1497c53b62e3d311b0f63802fb1dc0518cdb0dd57b67cd712f459"


def _sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _record(
    intent_id: str,
    status: str = "passed",
    layer: str | None = None,
    decision: str | None = "answer",
) -> dict[str, object]:
    return {
        "intent_id": intent_id,
        "runtime_status": status,
        "failure_layer": layer,
        "error_type": None if status == "passed" else "SomeError",
        "decision": decision,
        "raw_model_output": {"capture": "generation_provider_recorder"},
        "retrieval_query": "q",
        "top3_chunk_ids": ["c1"],
        "translation_call_count": 1,
        "retrieval_call_count": 1,
        "generation_call_count": 1,
        "translation_latency_ms": 1.0,
        "retrieval_latency_ms": 1.0,
        "generation_latency_ms": 1.0,
        "total_latency_ms": 3.0,
        "generation_eval_count": 10,
        "generation_prompt_eval_count": 700,
    }


def test_english_prompt_is_still_byte_identical_to_reliability_v1() -> None:
    """The branches share a module, so the English prompt must be re-checked."""

    assert _sha_text(SYSTEM_PROMPT) == FROZEN_EN_PROMPT_SHA
    assert PROMPT_VERSION == "grounded_answer_prompt_v1"


def test_vietnamese_prompt_was_rolled_back_after_the_candidate_failed() -> None:
    """The active runtime returns to the M4 prompt after frozen M5.1 rejected v2."""

    assert VI_SYSTEM_PROMPT == SYSTEM_PROMPT + "\nWrite an answer in Vietnamese."
    assert VI_PROMPT_VERSION == "grounded_answer_prompt_vi_v1"


def test_user_prompt_is_untouched() -> None:
    candidates = [{"rank": 1, "chunk_id": "c1", "chunk_text": "excerpt"}]
    assert build_user_prompt("Q", candidates, "en").startswith("Question:\n")
    assert build_user_prompt("Q", candidates, "vi").startswith("Answer language: vi\nQuestion:\n")


def test_m5_reuses_the_m4_capture_and_classification_helpers() -> None:
    """Identical objects, so both milestones classify and capture failures the same way."""

    assert runner.classify_failure is m4_runner.classify_failure
    assert runner.stage_telemetry is m4_runner.stage_telemetry
    assert runner.raw_output_from_recorder is m4_runner.raw_output_from_recorder
    assert runner.RecordingGenerationProvider is m4_runner.RecordingGenerationProvider


def test_gate_g2_counts_every_failure_layer_not_only_generation_contract() -> None:
    """The revision 1 hole: a run could pass G2 while failing at the translation layer."""

    records = [_record("a"), _record("b", status="failed", layer="translation_contract", decision=None)]
    summary = summarise(records)
    scope = {"result": "PASS"}

    gates = evaluate_gates(records, summary, [], scope, ["a", "b"], expected_intent_count=2)

    assert summary["failure_layer_counts"]["generation_contract"] == 0
    assert summary["total_runtime_failure_count"] == 1
    assert gates["conditions"]["G2_runtime_failure"]["result"] == "FAIL"
    assert gates["conditions"]["G2_runtime_failure"]["generation_contract_failure_count"] == 0
    assert gates["all_passed"] is False


def test_gate_g2_passes_only_on_a_completely_clean_run() -> None:
    records = [_record("a"), _record("b", decision="abstain")]
    summary = summarise(records)

    gates = evaluate_gates(records, summary, [], {"result": "PASS"}, ["a", "b"], expected_intent_count=2)

    assert summary["total_runtime_failure_count"] == 0
    assert summary["valid_abstention_count"] == 1
    assert gates["conditions"]["G2_runtime_failure"]["result"] == "PASS"
    assert gates["all_passed"] is True


def test_gate_g1_fails_when_runtime_hashes_move_during_execution() -> None:
    records = [_record("a")]
    summary = summarise(records)

    gates = evaluate_gates(
        records, summary, ["src/grounded_answer/service.py"], {"result": "PASS"}, ["a"], expected_intent_count=1
    )

    assert gates["conditions"]["G1_execution_integrity"]["result"] == "FAIL"
    assert gates["all_passed"] is False


def test_frozen_m5_scope_detects_rollback_and_later_m5_3_candidate() -> None:
    prereg = json.loads(M5_PREREGISTRATION.read_text(encoding="utf-8"))

    report = scope_integrity_report(prereg)

    assert report["observed_changed_files"] == ["src/grounded_answer/service.py"]
    assert report["unauthorized_changed_files"] == ["src/grounded_answer/service.py"]
    assert report["authorized_files_without_change"] == ["src/grounded_answer/prompts.py"]
    assert report["en_system_prompt_unchanged"] is True
    assert report["prompt_symbols"]["mismatched_symbols"] == [
        "vi_prompt_version",
        "vi_system_prompt_sha256",
    ]
    assert report["result"] == "FAIL"


def test_scope_integrity_rejects_a_second_changed_runtime_file() -> None:
    prereg = json.loads(M5_PREREGISTRATION.read_text(encoding="utf-8"))
    prereg["scope_integrity"]["baseline_runtime_sources_sha256_lf_normalized"][
        "src/grounded_answer/service.py"
    ] = "0" * 64

    report = scope_integrity_report(prereg)

    assert report["unauthorized_changed_files"] == ["src/grounded_answer/service.py"]
    assert report["result"] == "FAIL"


def test_scope_integrity_rejects_an_english_prompt_change() -> None:
    prereg = json.loads(M5_PREREGISTRATION.read_text(encoding="utf-8"))
    prereg["scope_integrity"]["prompt_symbols"]["en_system_prompt_sha256"] = "0" * 64

    report = scope_integrity_report(prereg)

    assert report["en_system_prompt_unchanged"] is False
    assert report["result"] == "FAIL"


def test_preregistration_locks_the_corrected_gate_and_the_pins() -> None:
    prereg = json.loads(M5_PREREGISTRATION.read_text(encoding="utf-8"))

    assert prereg["status"] == "preregistered_not_executed"
    assert prereg["preregistration_revision"] >= 2
    assert "total_runtime_failure_count equals zero" in prereg["acceptance_gates"]["G2_runtime_failure"]
    assert prereg["scope_integrity"]["authorized_changed_files"] == ["src/grounded_answer/prompts.py"]
    assert prereg["scope_integrity"]["prompt_symbols"]["en_system_prompt_sha256"] == FROZEN_EN_PROMPT_SHA
    assert set(prereg["analysis_code_sha256_lf_normalized"]) == {
        "scripts/evaluation/run_multilingual_runtime_v1_m5.py",
        "scripts/evaluation/run_multilingual_runtime_v1_m4.py",
        "scripts/evaluation/run_multilingual_runtime_v1_m3.py",
    }
    assert runner.analysis_code_mismatches(prereg) == []
    assert runner.runtime_source_mismatches(prereg) == [
        "src/grounded_answer/prompts.py",
        "src/grounded_answer/service.py",
    ]
    assert "contract_must_not_be_weakened" in prereg


def _current_prompt_pins() -> dict[str, str]:
    return {
        "en_system_prompt_sha256": _sha_text(SYSTEM_PROMPT),
        "en_prompt_version": PROMPT_VERSION,
        "build_user_prompt_source_sha256": _sha_text(
            inspect.getsource(build_user_prompt).replace("\r\n", "\n")
        ),
        "vi_system_prompt_sha256": _sha_text(VI_SYSTEM_PROMPT),
        "vi_prompt_version": VI_PROMPT_VERSION,
    }


def _runtime_matched_preregistration(tmp_path: Path, filename: str = "m5_preregistration.json") -> Path:
    """Build a temporary verifier fixture for today's rolled-back runtime.

    The frozen pre-registration itself remains untouched and correctly refuses this
    runtime. The fixture preserves a positive test for the verification mechanism.
    """

    prereg = json.loads(M5_PREREGISTRATION.read_text(encoding="utf-8"))
    rejected_runtime = dict(prereg["runtime_under_test"]["source_sha256_lf_normalized"])
    prereg["runtime_under_test"]["source_sha256_lf_normalized"] = {
        relative_path: runner.sha256_file_lf(PROJECT_ROOT / relative_path)
        for relative_path in prereg["runtime_under_test"]["source_sha256_lf_normalized"]
    }
    prereg["scope_integrity"]["baseline_runtime_sources_sha256_lf_normalized"] = {
        relative_path: runner.sha256_file_lf(PROJECT_ROOT / relative_path)
        for relative_path in prereg["scope_integrity"]["baseline_runtime_sources_sha256_lf_normalized"]
    }
    prereg["scope_integrity"]["baseline_runtime_sources_sha256_lf_normalized"][
        "src/grounded_answer/prompts.py"
    ] = rejected_runtime["src/grounded_answer/prompts.py"]
    prereg["scope_integrity"]["prompt_symbols"] = _current_prompt_pins()
    path = tmp_path / filename
    path.write_text(json.dumps(prereg, ensure_ascii=False), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("section", "key"),
    [
        ("analysis_code_sha256_lf_normalized", "scripts/evaluation/run_multilingual_runtime_v1_m5.py"),
        ("frozen_inputs_sha256", "data/gold/mit_60001/chunks.jsonl"),
    ],
)
def test_runner_refuses_to_start_on_a_hash_mismatch(
    section: str, key: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A wrong hash must stop the run before the encoder and before Ollama."""

    tampered = json.loads(M5_PREREGISTRATION.read_text(encoding="utf-8"))
    tampered[section][key] = "0" * 64
    tampered_path = tmp_path / "m5_preregistration.json"
    tampered_path.write_text(json.dumps(tampered, ensure_ascii=False), encoding="utf-8")

    monkeypatch.setattr(runner, "PREREGISTRATION", tampered_path)
    monkeypatch.setattr(sys, "argv", ["run_multilingual_runtime_v1_m5.py", "--verify-only"])

    with pytest.raises(ValueError):
        runner.main()

    assert not any((tmp_path / name).exists() for name in RESULT_ARTIFACT_NAMES)


def test_runner_refuses_to_start_when_scope_integrity_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    tampered = json.loads(_runtime_matched_preregistration(tmp_path).read_text(encoding="utf-8"))
    tampered["scope_integrity"]["prompt_symbols"]["en_system_prompt_sha256"] = "0" * 64
    tampered_path = tmp_path / "m5_preregistration_scope_drift.json"
    tampered_path.write_text(json.dumps(tampered, ensure_ascii=False), encoding="utf-8")

    monkeypatch.setattr(runner, "PREREGISTRATION", tampered_path)
    monkeypatch.setattr(sys, "argv", ["run_multilingual_runtime_v1_m5.py", "--verify-only"])

    with pytest.raises(ValueError, match="Scope integrity failed before execution"):
        runner.main()


def _result_artifact_state() -> dict[str, str | None]:
    state: dict[str, str | None] = {}
    for name in RESULT_ARTIFACT_NAMES:
        path = REPORT_DIR / name
        state[name] = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    return state


def test_frozen_m5_runner_refuses_the_rolled_back_runtime_without_touching_artifacts() -> None:
    script = PROJECT_ROOT / "scripts/evaluation/run_multilingual_runtime_v1_m5.py"
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
    assert "src/grounded_answer/prompts.py" in completed.stderr
    assert _result_artifact_state() == before


def test_verify_only_positive_path_works_with_a_runtime_matched_fixture(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fixture = _runtime_matched_preregistration(tmp_path)
    monkeypatch.setattr(runner, "PREREGISTRATION", fixture)
    monkeypatch.setattr(sys, "argv", ["run_multilingual_runtime_v1_m5.py", "--verify-only"])
    before = _result_artifact_state()

    runner.main()

    assert _result_artifact_state() == before


def test_runner_refuses_to_overwrite_existing_results(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(runner, "REPORT_DIR", tmp_path)
    (tmp_path / RESULT_ARTIFACT_NAMES[0]).write_text("{}", encoding="utf-8")

    with pytest.raises(FileExistsError):
        runner.ensure_no_existing_result_artifacts()


# --- Revision 4: per-stage diagnostics, full-pipeline proof and per-symbol scope ---


def test_diagnostic_gaps_are_clean_on_a_complete_record() -> None:
    record = _record("a")
    record["generation_prompt_eval_count"] = 700
    assert diagnostic_gaps(record) == []


@pytest.mark.parametrize(
    ("dropped_field", "expected_gap"),
    [
        ("retrieval_query", "retrieval_query"),
        ("top3_chunk_ids", "top3_chunk_ids"),
        ("raw_model_output", "raw_model_output"),
        ("generation_latency_ms", "generation_latency_ms"),
        ("generation_prompt_eval_count", "generation_prompt_eval_count"),
        ("generation_eval_count", "generation_eval_count"),
        ("translation_latency_ms", "translation_latency_ms"),
        ("retrieval_latency_ms", "retrieval_latency_ms"),
    ],
)
def test_every_required_diagnostic_is_detected_when_missing(dropped_field: str, expected_gap: str) -> None:
    """Losing any one required field must be named, not silently tolerated."""

    record = _record("a", status="failed", layer="generation_contract", decision=None)
    record["generation_prompt_eval_count"] = 700
    record[dropped_field] = None if dropped_field != "top3_chunk_ids" else []

    gaps = diagnostic_gaps(record)

    assert expected_gap in gaps


def test_translation_layer_failure_is_not_asked_for_downstream_diagnostics() -> None:
    """Retrieval never ran, so Top 3 must not be required from this record."""

    record = _record("a", status="failed", layer="translation_contract", decision=None)
    record.update(
        {
            "retrieval_query": None,
            "top3_chunk_ids": [],
            "raw_model_output": None,
            "retrieval_call_count": 0,
            "generation_call_count": 0,
            "retrieval_latency_ms": None,
            "generation_latency_ms": None,
            "generation_eval_count": None,
        }
    )

    assert diagnostic_gaps(record) == []


def test_gate_g1_fails_when_a_failed_record_lost_a_required_diagnostic() -> None:
    """The M3 data loss must not be able to pass G1."""

    good = _record("a")
    good["generation_prompt_eval_count"] = 700
    lost = _record("b", status="failed", layer="generation_contract", decision=None)
    lost["generation_prompt_eval_count"] = 700
    lost["retrieval_query"] = None
    lost["top3_chunk_ids"] = []
    records = [good, lost]
    summary = summarise(records)

    gates = evaluate_gates(records, summary, [], {"result": "PASS"}, ["a", "b"], expected_intent_count=2)

    g1 = gates["conditions"]["G1_execution_integrity"]
    assert g1["result"] == "FAIL"
    assert set(g1["diagnostic_gaps_by_intent"]["b"]) >= {"retrieval_query", "top3_chunk_ids"}


def test_gate_g1_fails_when_the_intent_set_or_order_differs() -> None:
    records = [_record("b"), _record("a")]
    for record in records:
        record["generation_prompt_eval_count"] = 700
    summary = summarise(records)

    gates = evaluate_gates(records, summary, [], {"result": "PASS"}, ["a", "b"], expected_intent_count=2)

    g1 = gates["conditions"]["G1_execution_integrity"]
    assert g1["intent_ids_match_preregistered_order"] is False
    assert g1["result"] == "FAIL"


def test_gate_g1_fails_when_a_passed_record_skipped_a_stage() -> None:
    """A record marked passed with zero model calls must not count as a clean run."""

    hollow = _record("a")
    hollow.update({"translation_call_count": 0, "retrieval_call_count": 0, "generation_call_count": 0})
    records = [hollow]
    summary = summarise(records)

    gates = evaluate_gates(records, summary, [], {"result": "PASS"}, ["a"], expected_intent_count=1)

    g1 = gates["conditions"]["G1_execution_integrity"]
    assert g1["passed_records_missing_a_stage_call"] == ["a"]
    assert g1["full_pipeline_on_every_passed_record"] is False
    assert g1["result"] == "FAIL"


def test_gate_g1_reports_stage_totals_on_a_clean_run() -> None:
    records = [_record("a"), _record("b")]
    for record in records:
        record["generation_prompt_eval_count"] = 700
    summary = summarise(records)

    gates = evaluate_gates(records, summary, [], {"result": "PASS"}, ["a", "b"], expected_intent_count=2)

    g1 = gates["conditions"]["G1_execution_integrity"]
    assert g1["stage_call_totals"] == {"translation": 2, "retrieval": 2, "generation": 2}
    assert g1["stage_totals_complete_when_run_is_clean"] is True
    assert g1["result"] == "PASS"


def test_prompt_symbols_are_pinned_with_roles() -> None:
    prereg = json.loads(M5_PREREGISTRATION.read_text(encoding="utf-8"))

    report = prompt_symbol_report(prereg)

    assert report["result"] == "FAIL", "the frozen candidate must detect the rollback"
    assert report["frozen_symbols_unchanged"] is True
    assert report["symbols"]["en_system_prompt_sha256"]["role"] == "frozen"
    assert report["symbols"]["en_prompt_version"]["role"] == "frozen"
    assert report["symbols"]["build_user_prompt_source_sha256"]["role"] == "frozen"
    assert report["symbols"]["vi_system_prompt_sha256"]["role"] == "authorized_candidate"
    assert report["symbols"]["vi_prompt_version"]["role"] == "authorized_candidate"


@pytest.mark.parametrize(
    "symbol",
    [
        "en_system_prompt_sha256",
        "en_prompt_version",
        "build_user_prompt_source_sha256",
        "vi_system_prompt_sha256",
        "vi_prompt_version",
    ],
)
def test_any_prompt_symbol_drift_fails_scope_integrity(symbol: str, tmp_path: Path) -> None:
    """A change to any pinned symbol must fail, not just a change to the file."""

    prereg = json.loads(_runtime_matched_preregistration(tmp_path).read_text(encoding="utf-8"))
    prereg["scope_integrity"]["prompt_symbols"][symbol] = "drifted"

    report = scope_integrity_report(prereg)

    assert report["prompt_symbols"]["mismatched_symbols"] == [symbol]
    assert report["result"] == "FAIL"


def test_preregistration_states_the_two_symbol_contract() -> None:
    prereg = json.loads(M5_PREREGISTRATION.read_text(encoding="utf-8"))
    change = prereg["single_authorized_runtime_change"]

    assert change["symbol_count"] == 2
    assert change["behavioral_change_count"] == 1
    assert change["symbols"]["VI_SYSTEM_PROMPT"]["role"] == "behavioral"
    assert change["symbols"]["VI_PROMPT_VERSION"]["role"] == "identity_and_provenance_only"
    assert change["symbols"]["VI_PROMPT_VERSION"]["not_a_behavioral_change"] is True
    assert "required_diagnostics_by_stage" in prereg["execution_protocol"]
