"""Validate M6 provenance preparation and a later isolated reproduction."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import subprocess
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = PROJECT_ROOT / "reports/37_m6_provenance_remediation"
PREREGISTRATION = REPORT_DIR / "m6_provenance_preregistration.json"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json_bytes(value: bytes) -> dict[str, Any]:
    return json.loads(value.decode("utf-8"))


def load_json_file(path: Path) -> dict[str, Any]:
    return load_json_bytes(path.read_bytes())


def load_csv_bytes(value: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(value.decode("utf-8-sig"), newline="")))


def git_blob_bytes(commit: str, relative_path: str) -> bytes:
    return subprocess.check_output(
        ["git", "show", f"{commit}:{relative_path}"], cwd=PROJECT_ROOT
    )


def frozen_artifact_bytes(prereg: dict[str, Any], name: str) -> bytes:
    artifact = prereg["frozen_artifacts"][name]
    value = git_blob_bytes(prereg["problem"]["freeze_commit"], artifact["path"])
    if sha256_bytes(value) != artifact["sha256"]:
        raise ValueError(f"Frozen artifact identity mismatch: {artifact['path']}")
    return value


def validate_frozen_sources(prereg: dict[str, Any]) -> None:
    commit = prereg["problem"]["freeze_commit"]
    for relative_path, expected_hash in prereg["frozen_sources"].items():
        observed_hash = sha256_bytes(git_blob_bytes(commit, relative_path))
        if observed_hash != expected_hash:
            raise ValueError(f"Frozen source identity mismatch: {relative_path}")


def rows_as_projection(rows: list[dict[str, str]], fields: list[str]) -> list[list[str]]:
    return [[row[field] for field in fields] for row in rows]


def validate_metric_projection(metrics: dict[str, Any], aggregate: dict[str, Any]) -> None:
    for field in (
        "decision_correct",
        "language_compliance",
        "strict_end_to_end_success",
        "strict_answer_success_diagnostic",
    ):
        observed = metrics[field]
        expected = aggregate[field]
        if (
            observed["numerator"] != expected["numerator"]
            or observed["denominator"] != expected["denominator"]
        ):
            raise ValueError(f"Metric differs from preregistered projection: {field}")


def validate_gate_projection(evaluation: dict[str, Any], aggregate: dict[str, Any]) -> None:
    observed = evaluation["gates"]["conditions"]
    expected = aggregate["gates"]
    if set(observed) != set(expected):
        raise ValueError("M6 gate set differs from preregistered projection")
    for gate, expected_result in expected.items():
        if observed[gate].get("result") != expected_result:
            raise ValueError(f"M6 gate differs from preregistered projection: {gate}")


def validate_preparation(prereg: dict[str, Any]) -> None:
    if prereg["execution_status"] != "NOT_RUN":
        raise ValueError("Preparation preregistration must remain NOT_RUN before reproduction")
    problem = prereg["problem"]
    worksheet = frozen_artifact_bytes(prereg, "reviewed_worksheet")
    evaluation = load_json_bytes(frozen_artifact_bytes(prereg, "original_evaluation_manifest"))
    final = load_json_bytes(frozen_artifact_bytes(prereg, "original_final_manifest"))
    results = load_csv_bytes(frozen_artifact_bytes(prereg, "original_final_results"))
    metrics = load_json_bytes(frozen_artifact_bytes(prereg, "original_metrics"))["metrics"]
    if sha256_bytes(worksheet) != problem["committed_reproduction_input_sha256"]:
        raise ValueError("Frozen reviewed worksheet differs from preregistered identity")
    if evaluation["reviewed_worksheet_sha256"] != problem["original_recorded_sha256"]:
        raise ValueError("Original evaluation manifest no longer records the known mismatch")
    if final["m6_e_artifacts_sha256"]["reviewed_worksheet"] != problem["original_recorded_sha256"]:
        raise ValueError("Original final manifest no longer records the known mismatch")
    if problem["original_recorded_sha256"] == problem["committed_reproduction_input_sha256"]:
        raise ValueError("Known mismatch is absent")
    actual_projection = rows_as_projection(results, prereg["row_fields"])
    expected_projection = prereg["per_intent_projection"]
    if actual_projection != expected_projection:
        for expected, observed in zip(expected_projection, actual_projection):
            if expected != observed:
                raise ValueError(
                    "Frozen final-results projection differs for "
                    f"{observed[0]}: expected={expected}; observed={observed}"
                )
        raise ValueError("Frozen final-results projection row count differs")
    validate_metric_projection(metrics, prereg["aggregate_projection"])
    validate_gate_projection(evaluation, prereg["aggregate_projection"])
    validate_frozen_sources(prereg)


def reproduction_input_failure(prereg: dict[str, Any], reproduction_repo: Path) -> str | None:
    expected_commit = prereg["problem"]["freeze_commit"]
    try:
        actual_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=reproduction_repo, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "reproduction checkout is not a readable Git repository"
    if actual_commit != expected_commit:
        return f"checkout HEAD is {actual_commit}, expected {expected_commit}"
    worksheet = prereg["frozen_artifacts"]["reviewed_worksheet"]
    worksheet_path = reproduction_repo / worksheet["path"]
    if not worksheet_path.is_file():
        return f"canonical worksheet is missing: {worksheet['path']}"
    if sha256_file(worksheet_path) != worksheet["sha256"]:
        return "canonical worksheet identity differs from preregistration"
    for relative_path, expected_hash in prereg["frozen_sources"].items():
        source_path = reproduction_repo / relative_path
        if not source_path.is_file() or sha256_file(source_path) != expected_hash:
            return f"frozen source identity differs: {relative_path}"
    return None


def compare_reproduction(prereg: dict[str, Any], reproduction_repo: Path) -> str:
    input_failure = reproduction_input_failure(prereg, reproduction_repo)
    if input_failure is not None:
        return f"CASE_C: pre-execution input gate failed: {input_failure}"
    report_dir = reproduction_repo / "reports/35_multilingual_runtime_v1_m6"
    results_path = report_dir / "m6_final_results.csv"
    metrics_path = report_dir / "m6_metrics.json"
    evaluation_path = report_dir / "m6_evaluation_manifest.json"
    if not all(path.is_file() for path in (results_path, metrics_path, evaluation_path)):
        return "CASE_C: required reproduction outputs are missing"
    results = load_csv_bytes(results_path.read_bytes())
    metrics = load_json_file(metrics_path)["metrics"]
    evaluation = load_json_file(evaluation_path)
    try:
        if rows_as_projection(results, prereg["row_fields"]) != prereg["per_intent_projection"]:
            return "CASE_B: per-intent projection differs"
        validate_metric_projection(metrics, prereg["aggregate_projection"])
        validate_gate_projection(evaluation, prereg["aggregate_projection"])
        if evaluation["reviewed_worksheet_sha256"] != prereg["problem"]["committed_reproduction_input_sha256"]:
            return "CASE_B: reproduction did not record the canonical worksheet identity"
    except (KeyError, ValueError) as error:
        return f"CASE_B: {error}"
    return "CASE_A: preregistered projection matches"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--reproduction-repo", type=Path)
    modes.add_argument("--verify-reproduction-input", type=Path)
    args = parser.parse_args()
    prereg = load_json_file(PREREGISTRATION)
    validate_preparation(prereg)
    if args.verify_reproduction_input is not None:
        failure = reproduction_input_failure(prereg, args.verify_reproduction_input.resolve())
        if failure is None:
            print("PRE_EXECUTION_PASS: canonical checkout input and source identities match")
        else:
            print(f"CASE_C: pre-execution input gate failed: {failure}")
            raise SystemExit(2)
        return
    if args.reproduction_repo is None:
        print("M6 provenance preparation verified; reproduction_status=NOT_RUN")
        return
    print(compare_reproduction(prereg, args.reproduction_repo.resolve()))


if __name__ == "__main__":
    main()
