"""Evaluate frozen M1 + M2 artifacts; never run retrieval or translation in M3."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import statistics
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
M1_ARTIFACT = PROJECT_ROOT / "evaluation/mit_60001/multilingual/paired_intents_v1.jsonl"
M1_MANIFEST = PROJECT_ROOT / "evaluation/mit_60001/multilingual/m1_manifest.json"
M2_RESULTS = PROJECT_ROOT / "reports/27_multilingual_dense_retrieval/multilingual_dense_retrieval_results.jsonl"
M2_MANIFEST = PROJECT_ROOT / "reports/27_multilingual_dense_retrieval/multilingual_dense_retrieval_manifest.json"
GOLD_FILE = PROJECT_ROOT / "data/gold/mit_60001/chunks.jsonl"
SILVER_FILE = PROJECT_ROOT / "data/silver/mit_60001/transcripts_clean.jsonl"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports/28_multilingual_retrieval_evaluation"
RESULTS_NAME = "multilingual_retrieval_evaluation_results.csv"
METRICS_NAME = "multilingual_retrieval_metrics.json"
MANIFEST_NAME = "multilingual_retrieval_evaluation_manifest.json"
README_NAME = "README.md"
BOUNDARY_TOLERANCE = 1e-6
HEADLINE_METRICS = ("mrr", "recall_at_1", "recall_at_3", "recall_at_5", "full_evidence_at_3")
CONTROL_IDS = ("mit60001-q-003", "mit60001-q-022")
TRACE_ID = "mit60001-q-008"


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_bytes(content)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def serialize_csv(rows: list[dict]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")


def resolve_ranges(paired: dict, silver_by_video: dict[str, dict]) -> list[dict]:
    resolved = []
    for range_index, ground_truth in enumerate(paired["ground_truth_ranges"], start=1):
        segments = silver_by_video[ground_truth["video_id"]]["segments"]
        starts = [
            segment["segment_index"]
            for segment in segments
            if abs(segment["start_second"] - ground_truth["start_second"]) < BOUNDARY_TOLERANCE
        ]
        ends = [
            segment["segment_index"]
            for segment in segments
            if abs(segment["start_second"] + segment["duration_second"] - ground_truth["end_second"])
            < BOUNDARY_TOLERANCE
        ]
        if len(starts) != 1 or len(ends) != 1 or ends[0] < starts[0]:
            raise ValueError(f"Canonical Ground Truth boundary mapping failed: {paired['intent_id']} range {range_index}")
        resolved.append(
            {
                "range_index": range_index,
                "video_id": ground_truth["video_id"],
                "source_segment_start_index": starts[0],
                "source_segment_end_index": ends[0],
            }
        )
    return resolved


def covered_range_indices(chunk: dict, ranges: list[dict]) -> list[int]:
    return [
        item["range_index"]
        for item in ranges
        if chunk["video_id"] == item["video_id"]
        and chunk["source_segment_start_index"] <= item["source_segment_end_index"]
        and chunk["source_segment_end_index"] >= item["source_segment_start_index"]
    ]


def branch_metrics(ranking: dict, chunk_by_id: dict[str, dict], ranges: list[dict]) -> dict:
    all_ranges = {item["range_index"] for item in ranges}
    first_relevant_rank = None
    top_3_covered = set()
    for result in ranking["results"]:
        covered = covered_range_indices(chunk_by_id[result["chunk_id"]], ranges)
        if covered and first_relevant_rank is None:
            first_relevant_rank = result["rank"]
        if result["rank"] <= 3:
            top_3_covered.update(covered)
    if first_relevant_rank is None:
        raise ValueError(f"Relevant evidence is unreachable: {ranking['intent_id']} {ranking['query_variant']}")
    return {
        "first_relevant_rank": first_relevant_rank,
        "reciprocal_rank": 1.0 / first_relevant_rank,
        "recall_at_1": int(first_relevant_rank <= 1),
        "recall_at_3": int(first_relevant_rank <= 3),
        "recall_at_5": int(first_relevant_rank <= 5),
        "full_evidence_at_3": int(top_3_covered == all_ranges),
    }


def aggregate(branch_rows: list[dict]) -> dict:
    return {
        "mrr": round(statistics.fmean(row["reciprocal_rank"] for row in branch_rows), 9),
        "recall_at_1": round(statistics.fmean(row["recall_at_1"] for row in branch_rows), 9),
        "recall_at_3": round(statistics.fmean(row["recall_at_3"] for row in branch_rows), 9),
        "recall_at_5": round(statistics.fmean(row["recall_at_5"] for row in branch_rows), 9),
        "full_evidence_at_3": round(statistics.fmean(row["full_evidence_at_3"] for row in branch_rows), 9),
    }


def validated_inputs() -> tuple[list[dict], list[dict], list[dict], list[dict], dict, dict]:
    m1_manifest = json.loads(M1_MANIFEST.read_text(encoding="utf-8"))
    m2_manifest = json.loads(M2_MANIFEST.read_text(encoding="utf-8"))
    if m1_manifest["status"] != "frozen" or m1_manifest["m1_gate_status"] != "passed":
        raise ValueError("M1 is not frozen/passed")
    if m2_manifest["status"] != "retrieval_complete" or m2_manifest["validation_status"] != "passed":
        raise ValueError("M2 is not complete/passed")
    if m1_manifest["artifacts"]["paired_artifact"]["sha256"] != sha256_file(M1_ARTIFACT):
        raise ValueError("M1 paired artifact hash mismatch")
    if m2_manifest["m1"]["paired_artifact_sha256"] != sha256_file(M1_ARTIFACT):
        raise ValueError("M2 did not use current frozen M1 artifact")
    if m2_manifest["m1"]["manifest_sha256"] != sha256_file(M1_MANIFEST):
        raise ValueError("M2 did not use current frozen M1 manifest")
    if m2_manifest["artifacts"]["results"]["sha256"] != sha256_file(M2_RESULTS):
        raise ValueError("M2 result hash mismatch")
    if m2_manifest["execution"]["quality_metrics_computed"]:
        raise ValueError("M2 unexpectedly contains quality metrics")
    if m2_manifest["retrieval"]["retrieval_depth"] != 861:
        raise ValueError("M2 does not contain full-corpus ranking")

    paired_rows = load_jsonl(M1_ARTIFACT)
    ranking_rows = load_jsonl(M2_RESULTS)
    gold_rows = load_jsonl(GOLD_FILE)
    silver_rows = load_jsonl(SILVER_FILE)
    if len(paired_rows) != 20 or len(ranking_rows) != 40 or len(gold_rows) != 861 or len(silver_rows) != 38:
        raise ValueError("Frozen M1/M2/Gold/Silver counts changed")
    return paired_rows, ranking_rows, gold_rows, silver_rows, m1_manifest, m2_manifest


def compute_evaluation() -> tuple[list[dict], dict, dict]:
    paired_rows, ranking_rows, gold_rows, silver_rows, m1_manifest, m2_manifest = validated_inputs()
    chunk_by_id = {row["chunk_id"]: row for row in gold_rows}
    silver_by_video = {row["video_id"]: row for row in silver_rows}
    ranking_by_key = {(row["intent_id"], row["query_variant"]): row for row in ranking_rows}
    if len(ranking_by_key) != 40:
        raise ValueError("M2 contains duplicate intent/branch")

    per_intent = []
    en_branch = []
    vi_branch = []
    for paired in paired_rows:
        intent_id = paired["intent_id"]
        ranges = resolve_ranges(paired, silver_by_video)
        computed_relevant_ids = [
            chunk["chunk_id"]
            for chunk in gold_rows
            if covered_range_indices(chunk, ranges)
        ]
        if computed_relevant_ids != paired["relevant_chunk_ids"]:
            raise ValueError(f"M1 relevant chunk mapping changed: {intent_id}")
        en_ranking = ranking_by_key[(intent_id, "en_canonical")]
        vi_ranking = ranking_by_key[(intent_id, "vi_literal_en")]
        if en_ranking["query_text"] != paired["question_en"] or vi_ranking["query_text"] != paired["literal_en"]:
            raise ValueError(f"M2 query differs from frozen M1: {intent_id}")
        en = branch_metrics(en_ranking, chunk_by_id, ranges)
        vi = branch_metrics(vi_ranking, chunk_by_id, ranges)
        en_branch.append(en)
        vi_branch.append(vi)
        en_top_3 = [item["chunk_id"] for item in en_ranking["results"][:3]]
        vi_top_3 = [item["chunk_id"] for item in vi_ranking["results"][:3]]
        overlap_count = len(set(en_top_3) & set(vi_top_3))
        if vi["first_relevant_rank"] < en["first_relevant_rank"]:
            outcome = "improved"
        elif vi["first_relevant_rank"] > en["first_relevant_rank"]:
            outcome = "degraded"
        else:
            outcome = "unchanged"
        per_intent.append(
            {
                "intent_id": intent_id,
                "translation_review_status": paired["review_status"],
                "en_first_relevant_rank": en["first_relevant_rank"],
                "vi_first_relevant_rank": vi["first_relevant_rank"],
                "rank_delta_vi_minus_en": vi["first_relevant_rank"] - en["first_relevant_rank"],
                "en_reciprocal_rank": round(en["reciprocal_rank"], 12),
                "vi_reciprocal_rank": round(vi["reciprocal_rank"], 12),
                "en_recall_at_1": en["recall_at_1"],
                "vi_recall_at_1": vi["recall_at_1"],
                "en_recall_at_3": en["recall_at_3"],
                "vi_recall_at_3": vi["recall_at_3"],
                "en_recall_at_5": en["recall_at_5"],
                "vi_recall_at_5": vi["recall_at_5"],
                "en_full_evidence_at_3": en["full_evidence_at_3"],
                "vi_full_evidence_at_3": vi["full_evidence_at_3"],
                "top_3_overlap_count": overlap_count,
                "top_3_overlap_rate": round(overlap_count / 3, 9),
                "exact_top_3_match": en_top_3 == vi_top_3,
                "first_relevant_rank_outcome": outcome,
            }
        )

    en_aggregate = aggregate(en_branch)
    vi_aggregate = aggregate(vi_branch)
    headline = {
        metric: {
            "en_canonical": en_aggregate[metric],
            "vi_literal_en": vi_aggregate[metric],
            "delta_vi_minus_en": round(vi_aggregate[metric] - en_aggregate[metric], 9),
        }
        for metric in HEADLINE_METRICS
    }
    controls = {}
    per_intent_by_id = {row["intent_id"]: row for row in per_intent}
    control_fields = [
        "en_first_relevant_rank",
        "vi_first_relevant_rank",
        "en_recall_at_1",
        "vi_recall_at_1",
        "en_recall_at_3",
        "vi_recall_at_3",
        "en_recall_at_5",
        "vi_recall_at_5",
        "en_full_evidence_at_3",
        "vi_full_evidence_at_3",
    ]
    for intent_id in CONTROL_IDS:
        paired = next(row for row in paired_rows if row["intent_id"] == intent_id)
        row = per_intent_by_id[intent_id]
        passed = (
            paired["question_en"] == paired["literal_en"]
            and row["en_first_relevant_rank"] == row["vi_first_relevant_rank"]
            and row["en_recall_at_1"] == row["vi_recall_at_1"]
            and row["en_recall_at_3"] == row["vi_recall_at_3"]
            and row["en_recall_at_5"] == row["vi_recall_at_5"]
            and row["en_full_evidence_at_3"] == row["vi_full_evidence_at_3"]
        )
        controls[intent_id] = {
            "question_strings_identical": paired["question_en"] == paired["literal_en"],
            "branch_metrics_identical": passed,
            "validation_status": "passed" if passed else "failed",
        }
        if not passed:
            raise RuntimeError(f"Exact-string evaluator control failed: {intent_id}; fields={control_fields}")

    trace_row = per_intent_by_id[TRACE_ID]
    if trace_row["translation_review_status"] != "Minor wording difference":
        raise ValueError("q-008 translation review trace was not preserved")
    outcomes = Counter(row["first_relevant_rank_outcome"] for row in per_intent)
    evaluation_identity = {
        "artifact_version": "mit_60001_multilingual_m3_v1",
        "m1_paired_artifact_sha256": sha256_file(M1_ARTIFACT),
        "m1_manifest_sha256": sha256_file(M1_MANIFEST),
        "m2_results_sha256": sha256_file(M2_RESULTS),
        "m2_manifest_sha256": sha256_file(M2_MANIFEST),
        "gold_sha256": sha256_file(GOLD_FILE),
        "silver_sha256": sha256_file(SILVER_FILE),
        "metric_contract": list(HEADLINE_METRICS),
    }
    evaluation_id = "mit60001_multilingual_eval_" + sha256_bytes(canonical_json(evaluation_identity).encode("utf-8"))[:16]
    metrics = {
        "schema_version": "multilingual_retrieval_metrics_v1",
        "artifact_version": "mit_60001_multilingual_m3_v1",
        "evaluation_id": evaluation_id,
        "status": "descriptive_baseline_complete",
        "number_of_paired_intents": 20,
        "headline_metrics": headline,
        "paired_first_relevant_rank_outcomes": {
            "definition": "improved if VI rank < EN rank; unchanged if equal; degraded if VI rank > EN rank",
            "improved": outcomes["improved"],
            "unchanged": outcomes["unchanged"],
            "degraded": outcomes["degraded"],
        },
        "top_3_overlap_diagnostic": {
            "mean_overlap_rate": round(statistics.fmean(row["top_3_overlap_rate"] for row in per_intent), 9),
            "exact_top_3_match_count": sum(row["exact_top_3_match"] for row in per_intent),
            "intent_count": 20,
            "quality_metric": False,
        },
        "exact_string_controls": controls,
        "q_008_trace": {
            "translation_review_status": trace_row["translation_review_status"],
            "en_first_relevant_rank": trace_row["en_first_relevant_rank"],
            "vi_first_relevant_rank": trace_row["vi_first_relevant_rank"],
            "rank_delta_vi_minus_en": trace_row["rank_delta_vi_minus_en"],
            "first_relevant_rank_outcome": trace_row["first_relevant_rank_outcome"],
            "translation_modified_after_m2": False,
        },
        "quality_gate": {"defined": False, "reason": "descriptive baseline; no post-hoc threshold"},
    }
    provenance = {
        "evaluation_identity": evaluation_identity,
        "m1_manifest": m1_manifest,
        "m2_manifest": m2_manifest,
        "ground_truth_range_count": sum(len(row["ground_truth_ranges"]) for row in paired_rows),
    }
    return per_intent, metrics, provenance


def render_readme(metrics: dict) -> bytes:
    headline = metrics["headline_metrics"]
    rows = []
    labels = {
        "mrr": "MRR",
        "recall_at_1": "Recall@1",
        "recall_at_3": "Recall@3",
        "recall_at_5": "Recall@5",
        "full_evidence_at_3": "Full Evidence@3",
    }
    for metric in HEADLINE_METRICS:
        values = headline[metric]
        rows.append(
            f"| {labels[metric]} | {values['en_canonical']:.9f} | {values['vi_literal_en']:.9f} | {values['delta_vi_minus_en']:+.9f} |"
        )
    outcomes = metrics["paired_first_relevant_rank_outcomes"]
    overlap = metrics["top_3_overlap_diagnostic"]
    trace = metrics["q_008_trace"]
    content = f"""# Phase 9 M3 — Multilingual retrieval evaluation

## Scope

M3 chỉ đọc frozen M1 Ground Truth và M2 full rankings. Không chạy retrieval,
translator, query expansion, reranking hoặc human relabel.

## Headline metrics

| Metric | EN canonical | VI → literal EN | Δ VI - EN |
| --- | ---: | ---: | ---: |
{chr(10).join(rows)}

MRR dùng full ranking 861. Full Evidence@3 giữ canonical contract: Top 3 phải phủ
đủ mọi Ground Truth range của intent, không chỉ chứa một relevant chunk.

## Paired diagnostic

First relevant rank outcomes (`VI rank < / = / > EN rank`):

- Improved: {outcomes['improved']}
- Unchanged: {outcomes['unchanged']}
- Degraded: {outcomes['degraded']}

Mean Top-3 overlap: {overlap['mean_overlap_rate']:.9f}. Exact ordered Top-3 matches:
{overlap['exact_top_3_match_count']}/20. Đây là diagnostic, không phải quality metric.

Exact-string controls `mit60001-q-003` và `mit60001-q-022`: metrics giống nhau
giữa hai branches, validation `passed`.

`mit60001-q-008` giữ trace `Minor wording difference`: EN first relevant rank
{trace['en_first_relevant_rank']}, VI rank {trace['vi_first_relevant_rank']}, delta
{trace['rank_delta_vi_minus_en']:+d}, outcome `{trace['first_relevant_rank_outcome']}`.

## Boundary

Đây là descriptive baseline, không có post-hoc quality gate. M3 không tự mở
`expanded_en`, RRF hoặc experiment mới; quyết định tiếp theo cần user duyệt.
"""
    return content.encode("utf-8")


def build_artifacts() -> dict[str, bytes]:
    per_intent, metrics, provenance = compute_evaluation()
    results_bytes = serialize_csv(per_intent)
    metrics_bytes = (json.dumps(metrics, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    readme_bytes = render_readme(metrics)
    manifest = {
        "schema_version": "multilingual_retrieval_evaluation_manifest_v1",
        "artifact_version": "mit_60001_multilingual_m3_v1",
        "evaluation_id": metrics["evaluation_id"],
        "status": "descriptive_baseline_complete",
        "sources": {
            "m1_paired_artifact": {"path": "evaluation/mit_60001/multilingual/paired_intents_v1.jsonl", "sha256": sha256_file(M1_ARTIFACT)},
            "m1_manifest": {"path": "evaluation/mit_60001/multilingual/m1_manifest.json", "sha256": sha256_file(M1_MANIFEST)},
            "m2_results": {"path": "reports/27_multilingual_dense_retrieval/multilingual_dense_retrieval_results.jsonl", "sha256": sha256_file(M2_RESULTS)},
            "m2_manifest": {"path": "reports/27_multilingual_dense_retrieval/multilingual_dense_retrieval_manifest.json", "sha256": sha256_file(M2_MANIFEST)},
            "canonical_gold": {"path": "data/gold/mit_60001/chunks.jsonl", "sha256": sha256_file(GOLD_FILE)},
            "canonical_silver": {"path": "data/silver/mit_60001/transcripts_clean.jsonl", "sha256": sha256_file(SILVER_FILE)},
        },
        "evaluation_contract": {
            "number_of_paired_intents": 20,
            "mrr_ranking_depth": 861,
            "mrr_definition": "mean(1 / full-corpus rank of first chunk covering any Ground Truth range)",
            "recall_k_values": [1, 3, 5],
            "full_evidence_at_3_definition": "Top 3 union of covered Ground Truth range indices equals all required range indices",
            "relevance_rule": "same_video_and_source_segment_interval_intersection",
            "delta_definition": "VI literal_en minus EN canonical",
            "paired_outcome_definition": metrics["paired_first_relevant_rank_outcomes"]["definition"],
            "post_hoc_quality_gate_defined": False,
        },
        "execution": {
            "retrieval_rerun_count": 0,
            "translator_calls": 0,
            "llm_calls": 0,
            "ground_truth_modification_count": 0,
            "human_relabel_count": 0,
            "query_expansion_count": 0,
        },
        "validation": {
            "paired_intents_evaluated": len(per_intent),
            "ground_truth_range_count": provenance["ground_truth_range_count"],
            "exact_string_control_count": len(CONTROL_IDS),
            "exact_string_control_pass_count": sum(item["validation_status"] == "passed" for item in metrics["exact_string_controls"].values()),
            "q_008_trace_preserved": metrics["q_008_trace"]["translation_review_status"] == "Minor wording difference",
            "deterministic_in_process_rebuild": "passed",
        },
        "artifacts": {
            "results": {"path": "reports/28_multilingual_retrieval_evaluation/multilingual_retrieval_evaluation_results.csv", "sha256": sha256_bytes(results_bytes)},
            "metrics": {"path": "reports/28_multilingual_retrieval_evaluation/multilingual_retrieval_metrics.json", "sha256": sha256_bytes(metrics_bytes)},
            "readme": {"path": "reports/28_multilingual_retrieval_evaluation/README.md", "sha256": sha256_bytes(readme_bytes)},
        },
        "evaluator": {
            "path": "scripts/evaluation/evaluate_multilingual_retrieval_m3.py",
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "validation_status": "passed",
    }
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    return {
        RESULTS_NAME: results_bytes,
        METRICS_NAME: metrics_bytes,
        MANIFEST_NAME: manifest_bytes,
        README_NAME: readme_bytes,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    first = build_artifacts()
    second = build_artifacts()
    if first != second:
        raise RuntimeError("M3 evaluator in-process deterministic rebuild failed")
    output_dir = args.output_dir.resolve()
    for name, content in first.items():
        write_atomic(output_dir / name, content)
    metrics = json.loads(first[METRICS_NAME].decode("utf-8"))
    print(
        json.dumps(
            {
                "validation_status": "passed",
                "evaluation_id": metrics["evaluation_id"],
                "paired_intents_evaluated": 20,
                "headline_metrics": metrics["headline_metrics"],
                "paired_outcomes": metrics["paired_first_relevant_rank_outcomes"],
                "retrieval_rerun_count": 0,
                "translator_calls": 0,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
