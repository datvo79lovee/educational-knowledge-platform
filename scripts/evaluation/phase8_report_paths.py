"""Physical Phase 8 report paths with frozen-manifest compatibility."""

from __future__ import annotations

import hashlib
from pathlib import Path


PHASE8_PARENT = Path("reports/phase_08_evidence_reviewer")
LEGACY_REPORT_NAMES = {
    "13_evidence_review",
    "14_evidence_review_runtime",
    "15_evidence_reviewer_evaluation",
    "16_evidence_reviewer_prompt_experiment",
    "17_evidence_reviewer_prompt_evaluation",
    "18_evidence_reviewer_a1_experiment",
    "19_evidence_reviewer_a1_evaluation",
}
CURRENT_PREFIX = "reports/phase_08_evidence_reviewer/"
LEGACY_PREFIX = "reports/"


def legacy_manifest_path(path: str | Path, project_root: Path | None = None) -> str:
    """Return the pre-relocation path retained inside frozen manifests."""

    value = Path(path)
    if value.is_absolute():
        if project_root is None:
            raise ValueError("project_root is required for an absolute path")
        value = value.relative_to(project_root)
    normalized = value.as_posix()
    if normalized.startswith(CURRENT_PREFIX):
        remainder = normalized[len(CURRENT_PREFIX):]
        report_name = remainder.split("/", 1)[0]
        if report_name in LEGACY_REPORT_NAMES:
            return LEGACY_PREFIX + remainder
    return normalized


def resolve_manifest_path(project_root: Path, manifest_path: str | Path) -> Path:
    """Resolve a frozen legacy path to the current physical parent folder."""

    normalized = Path(manifest_path).as_posix()
    if normalized.startswith(LEGACY_PREFIX) and not normalized.startswith(CURRENT_PREFIX):
        remainder = normalized[len(LEGACY_PREFIX):]
        report_name = remainder.split("/", 1)[0]
        if report_name in LEGACY_REPORT_NAMES:
            return project_root / PHASE8_PARENT / remainder
    return project_root / normalized


def frozen_compatible_sha256(path: Path) -> str:
    """Hash source after reversing only the Phase 8 path-prefix relocation."""

    content = path.read_bytes().replace(
        CURRENT_PREFIX.encode("utf-8"), LEGACY_PREFIX.encode("utf-8")
    )
    return hashlib.sha256(content).hexdigest()
