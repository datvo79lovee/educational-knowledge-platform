"""Protocol tests for the frozen-output M6 Vietnamese quality evaluation."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

import scripts.evaluation.run_multilingual_runtime_v1_m6 as runner


PREREGISTRATION = runner.PREREGISTRATION
RESULT_PATHS = (
    runner.WORKSHEET,
    runner.PREPARATION_MANIFEST,
    runner.REVIEWED_WORKSHEET,
    runner.FINAL_RESULTS,
    runner.METRICS,
    runner.EVALUATION_MANIFEST,
)


def _artifact_state() -> dict[str, str | None]:
    return {
        str(path): hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
        for path in RESULT_PATHS
    }


def _evaluated_rows(*, decisions: int, strict_e2e: int) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for index in range(19):
        rows.append({
            "intent_id": f"q-{index:03d}",
            "evaluation_scope": "primary",
            "decision": "answer",
            "decision_correct": "true" if index < decisions else "false",
            "language_compliant": "true",
            "strict_answer_success": "true" if index < strict_e2e else "false",
            "strict_end_to_end_success": "true" if index < strict_e2e else "false",
        })
    rows.append({
        "intent_id": "mit60001-q-023",
        "evaluation_scope": "excluded_frozen_ground_truth_ambiguity",
        "decision": "abstain",
        "decision_correct": "true",
        "language_compliant": "true",
        "strict_answer_success": "false",
        "strict_end_to_end_success": "true",
    })
    return rows


def _outputs(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    return [
        {
            "intent_id": row["intent_id"],
            "retrieval_query": "query",
            "top3_chunk_ids": ["c1", "c2", "c3"],
            "normalization_applied": False,
            "normalization_reason": None,
        }
        for row in rows
    ]


def test_preregistration_locks_scope_baseline_gates_and_no_runtime_calls() -> None:
    prereg = json.loads(PREREGISTRATION.read_text(encoding="utf-8"))

    assert prereg["status"] == "preregistered_not_reviewed"
    assert prereg["evaluation_scope"]["worksheet_count"] == 20
    assert prereg["evaluation_scope"]["primary_evaluation_count"] == 19
    assert prereg["evaluation_scope"]["primary_excluded_intent_ids"] == ["mit60001-q-023"]
    assert prereg["frozen_english_matched_baseline"]["decision_correct_count"] == 11
    assert prereg["frozen_english_matched_baseline"]["strict_end_to_end_success_count"] == 7
    assert [gate["id"] for gate in prereg["primary_gate"]["conditions_all_must_hold"]] == [
        "G1", "G2", "G3", "G4"
    ]
    assert prereg["execution_policy"]["model_calls"] == 0
    assert prereg["execution_policy"]["retrieval_reruns"] == 0


def test_current_hashes_and_frozen_m5_3_authorization_verify() -> None:
    prereg = runner.verify_preregistration()

    assert prereg["base_commit"].startswith("f2429ee")


@pytest.mark.parametrize(
    ("section", "path"),
    [
        ("frozen_inputs_sha256", "reports/34_multilingual_runtime_v1_m5_3/m5_3_runtime_outputs.jsonl"),
        ("analysis_code_sha256_lf_normalized", "scripts/evaluation/run_multilingual_runtime_v1_m6.py"),
    ],
)
def test_hash_drift_is_rejected(section: str, path: str) -> None:
    prereg = json.loads(PREREGISTRATION.read_text(encoding="utf-8"))
    prereg[section][path] = "0" * 64

    with pytest.raises(ValueError, match="changed since M6 pre-registration"):
        runner.verify_hash_map(
            prereg[section], lf=section.startswith("analysis_code"), label="Test pin"
        )


def test_blind_worksheet_has_exact_scope_order_and_no_diagnostic_leakage() -> None:
    prereg = runner.verify_preregistration()
    rows = runner.build_worksheet_rows(prereg)
    forbidden = {
        "retrieval_query", "raw_model_output", "normalization_applied",
        "normalization_reason", "translation_status", "review_status",
    }

    assert len(rows) == 20
    assert sum(row["evaluation_scope"] == "primary" for row in rows) == 19
    assert [row["intent_id"] for row in rows] == prereg["human_review"]["worksheet_order"][
        "expected_intent_order"
    ]
    assert forbidden.isdisjoint(rows[0])
    assert all(not row[field] for row in rows for field in runner.REVIEW_FIELDS)


def test_protected_field_change_is_rejected() -> None:
    prereg = runner.verify_preregistration()
    canonical = runner.build_worksheet_rows(prereg)
    reviewed = [dict(row) for row in canonical]
    reviewed[0]["question_vi"] = "changed"

    with pytest.raises(ValueError, match="Protected M6 field changed"):
        runner.validate_reviewed_rows(prereg, canonical, reviewed)


def test_answer_and_abstain_label_rules_are_enforced() -> None:
    prereg = runner.verify_preregistration()
    canonical = runner.build_worksheet_rows(prereg)
    reviewed = [dict(row) for row in canonical]
    for row in reviewed:
        row["evidence_sufficiency"] = "Sufficient" if row["decision"] == "answer" else "Insufficient"
        row["decision_judgment"] = "Correct"
        for field in (
            "answer_correctness", "answer_completeness", "groundedness",
            "citation_support_overall", "output_language",
        ):
            row[field] = "N/A"

    with pytest.raises(ValueError, match="Answer row has N/A"):
        runner.validate_reviewed_rows(prereg, canonical, reviewed)


@pytest.mark.parametrize(
    ("decisions", "strict_e2e", "g3", "g4"),
    [(10, 6, "PASS", "PASS"), (9, 6, "FAIL", "PASS"), (10, 5, "PASS", "FAIL")],
)
def test_pre_registered_gate_boundaries(
    decisions: int, strict_e2e: int, g3: str, g4: str
) -> None:
    prereg = json.loads(PREREGISTRATION.read_text(encoding="utf-8"))
    rows = _evaluated_rows(decisions=decisions, strict_e2e=strict_e2e)

    result = runner.compute_metrics_and_gates(prereg, rows, _outputs(rows))

    assert result["gates"]["conditions"]["G3_decision_non_inferiority"]["result"] == g3
    assert result["gates"]["conditions"]["G4_strict_end_to_end_non_inferiority"]["result"] == g4


def test_post_review_diagnostics_do_not_claim_causal_attribution() -> None:
    prereg = json.loads(PREREGISTRATION.read_text(encoding="utf-8"))
    rows = _evaluated_rows(decisions=10, strict_e2e=6)

    diagnostics = runner.compute_metrics_and_gates(prereg, rows, _outputs(rows))["diagnostics"]

    assert diagnostics["role"] == "post-review_observation_only_no_causal_attribution"
    assert "do not establish" in diagnostics["interpretation_boundary"]


def test_verify_only_is_read_only() -> None:
    before = _artifact_state()

    completed = subprocess.run(
        [sys.executable, str(Path(runner.__file__)), "--verify-only"],
        cwd=runner.PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert completed.returncode == 0, completed.stderr
    assert _artifact_state() == before


def test_evaluation_outputs_do_not_exist_before_review() -> None:
    assert not runner.REVIEWED_WORKSHEET.exists()
    assert not runner.FINAL_RESULTS.exists()
    assert not runner.METRICS.exists()
    assert not runner.EVALUATION_MANIFEST.exists()
