from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

import scripts.evaluation.run_multilingual_runtime_v1_m3 as runner
from scripts.evaluation.run_multilingual_runtime_v1_m3 import (
    ATTEMPT_FAILURE,
    PRIMARY_EXCLUDED_IDS,
    PROJECT_ROOT,
    RE_REVIEW_ORDER_SEED,
    REVIEW_FIELDS,
    REVIEW_ORDER_SEED,
    build_review_rows,
    deterministic_intent_order,
    derive_frozen_english_baseline,
    select_re_review_ids,
    selected_inputs,
    serialize_csv,
    serialize_jsonl,
    wilson_interval,
)


def test_matched_english_baseline_is_the_locked_19_intent_scope() -> None:
    intents, _ = selected_inputs()

    baseline = derive_frozen_english_baseline({row["intent_id"] for row in intents})

    assert baseline == {
        "selected_count": 20,
        "evaluated_count": 19,
        "excluded_intent_ids": ["mit60001-q-023"],
        "decision_correct_count": 11,
        "answer_count": 8,
        "strict_answer_success_count": 2,
        "strict_end_to_end_success_count": 7,
    }


def test_review_worksheet_is_bom_encoded_and_carries_frozen_exclusion() -> None:
    _, questions = selected_inputs()
    output = {
        "intent_id": "mit60001-q-023",
        "runtime_status": "passed",
        "original_query": "Theo khóa học, abstraction được giải thích như thế nào?",
        "retrieval_query": "How is abstraction explained?",
        "decision": "abstain",
        "answer": None,
        "supporting_chunk_ids": [],
        "top3_chunk_ids": [],
    }

    rows = build_review_rows([output], questions)
    encoded = serialize_csv(rows)

    assert PRIMARY_EXCLUDED_IDS == {"mit60001-q-023"}
    assert rows[0]["evaluation_scope"] == "excluded_frozen_ground_truth_ambiguity"
    assert tuple(rows[0]) == REVIEW_FIELDS
    assert encoded.startswith(b"\xef\xbb\xbf")


def test_review_and_re_review_orders_match_preregistration() -> None:
    intents, _ = selected_inputs()
    intent_ids = [row["intent_id"] for row in intents]

    assert deterministic_intent_order(intent_ids, REVIEW_ORDER_SEED) == [
        "mit60001-q-014",
        "mit60001-q-003",
        "mit60001-q-021",
        "mit60001-q-023",
        "mit60001-q-029",
        "mit60001-q-008",
        "mit60001-q-001",
        "mit60001-q-039",
        "mit60001-q-020",
        "mit60001-q-022",
        "mit60001-q-010",
        "mit60001-q-025",
        "mit60001-q-037",
        "mit60001-q-016",
        "mit60001-q-033",
        "mit60001-q-002",
        "mit60001-q-006",
        "mit60001-q-005",
        "mit60001-q-034",
        "mit60001-q-004",
    ]
    assert RE_REVIEW_ORDER_SEED == "6000103-rereview"
    assert select_re_review_ids(intent_ids) == [
        "mit60001-q-022",
        "mit60001-q-016",
        "mit60001-q-020",
        "mit60001-q-005",
        "mit60001-q-014",
        "mit60001-q-039",
    ]


@pytest.mark.parametrize(
    ("successes", "expected"),
    [
        (11, (0.362759, 0.768581)),
        (7, (0.191495, 0.589605)),
        (2, (0.029359, 0.313941)),
    ],
)
def test_wilson_intervals_for_matched_english_baseline(
    successes: int, expected: tuple[float, float]
) -> None:
    actual = wilson_interval(successes, 19)

    assert actual == pytest.approx(expected, abs=0.000001)


def test_runtime_failure_is_recorded_once_and_stops_attempt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class FailingService:
        def __init__(self, **_: object) -> None:
            pass

        def answer(self, *_: object) -> None:
            raise RuntimeError("provider failed")

    class Counter:
        call_count = 0
        last_latency_ms = None

    raw_output = tmp_path / "runtime.jsonl"
    monkeypatch.setattr(runner, "GroundedAnswerService", FailingService)
    monkeypatch.setattr(runner, "RAW_OUTPUT", raw_output)

    rows = runner.execute_runtime(
        [
            {"intent_id": "mit60001-q-001", "question_vi": "Một"},
            {"intent_id": "mit60001-q-002", "question_vi": "Hai"},
        ],
        search_service=object(),
        translator=Counter(),
        generator=Counter(),
    )

    assert len(rows) == 1
    assert rows[0]["runtime_status"] == "failed"
    assert rows[0]["error_type"] == "RuntimeError"
    assert len(runner.load_jsonl(raw_output)) == 1


def test_interrupted_attempt_retains_partial_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    partial_output = tmp_path / "runtime.jsonl"
    failure_output = tmp_path / ATTEMPT_FAILURE.name
    partial_output.write_bytes(
        serialize_jsonl(
            [
                {
                    "intent_id": "mit60001-q-001",
                    "runtime_status": "passed",
                }
            ]
        )
    )
    monkeypatch.setattr(runner, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(runner, "RAW_OUTPUT", partial_output)
    monkeypatch.setattr(runner, "ATTEMPT_FAILURE", failure_output)

    runner.write_aborted_attempt(KeyboardInterrupt())
    artifact = runner.json.loads(failure_output.read_text(encoding="utf-8"))

    assert artifact["status"] == "aborted_incomplete"
    assert artifact["completed_record_count"] == 1
    assert artifact["quality_metrics_computed"] is False


def test_verify_only_runs_in_clean_subprocess_without_creating_results() -> None:
    script = PROJECT_ROOT / "scripts/evaluation/run_multilingual_runtime_v1_m3.py"
    completed = subprocess.run(
        [sys.executable, "-X", "utf8", str(script), "--verify-only"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert "no encoder load and no Ollama call was made" in completed.stdout
    report_dir = PROJECT_ROOT / "reports/31_multilingual_runtime_v1_m3"
    assert not (report_dir / "m3_runtime_outputs.jsonl").exists()
    assert not (report_dir / "m3_human_review_worksheet.csv").exists()
    assert not (report_dir / "m3_execution_manifest.json").exists()
