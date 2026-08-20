"""Tests for the non-destructive Phase 8 report relocation mapping."""

from __future__ import annotations

import hashlib
from pathlib import Path

from scripts.evaluation.phase8_report_paths import (
    frozen_compatible_sha256,
    legacy_manifest_path,
    resolve_manifest_path,
)


def test_current_report_path_maps_back_to_frozen_manifest_path() -> None:
    current = Path(
        "reports/phase_08_evidence_reviewer/18_evidence_reviewer_a1_experiment/"
        "a1_experiment_manifest.json"
    )
    assert legacy_manifest_path(current) == (
        "reports/18_evidence_reviewer_a1_experiment/a1_experiment_manifest.json"
    )


def test_frozen_manifest_path_resolves_to_current_physical_folder(tmp_path: Path) -> None:
    resolved = resolve_manifest_path(
        tmp_path,
        "reports/15_evidence_reviewer_evaluation/final_metrics.json",
    )
    assert resolved == tmp_path / (
        "reports/phase_08_evidence_reviewer/15_evidence_reviewer_evaluation/"
        "final_metrics.json"
    )


def test_frozen_compatible_hash_reverses_only_the_parent_relocation(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.py"
    source.write_bytes(
        b'REPORT_ROOT = "reports/phase_08_evidence_reviewer/'
        b'16_evidence_reviewer_prompt_experiment"\n'
    )
    expected = hashlib.sha256(
        b'REPORT_ROOT = "reports/16_evidence_reviewer_prompt_experiment"\n'
    ).hexdigest()
    assert frozen_compatible_sha256(source) == expected
