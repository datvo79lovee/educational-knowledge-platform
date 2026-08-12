"""So sánh dense retrieval cho ba MIT 6.0001 chunking configurations."""

import csv
import hashlib
import io
import json
import platform
import statistics
from pathlib import Path

import numpy as np
import sentence_transformers
from sentence_transformers import SentenceTransformer
import torch
import transformers


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVALUATION_FILE = Path("evaluation/mit_60001/evaluation_questions.jsonl")
SILVER_FILE = Path("data/silver/mit_60001/transcripts_clean.jsonl")
EXPERIMENT_ROOT = Path("data/gold/mit_60001/experiments")
FULL_VALIDATION_REPORT = Path("reports/08_chunking/full_chunk_validation.csv")
RESULTS_FILE = Path("reports/08_chunking/chunking_retrieval_results.csv")
COMPARISON_FILE = Path("reports/08_chunking/chunking_comparison.csv")
MANIFEST_FILE = Path("reports/08_chunking/retrieval_run_manifest.json")
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
CONFIG_IDS = (
    "fixed_wp240_o48_v1",
    "semantic_cosine_wp240_v1",
    "semantic_cosine_wp192_o32_v1",
)
K_VALUES = (1, 3, 5, 10)
BOUNDARY_TOLERANCE = 1e-6
RETRIEVAL_VERSION = "mit60001_dense_chunk_retrieval_v1"


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_bytes(value: dict) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_bytes(content)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_validation_rows() -> dict[str, dict]:
    with FULL_VALIDATION_REPORT.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    by_config = {row["chunking_config_id"]: row for row in rows}
    if set(by_config) != set(CONFIG_IDS):
        raise ValueError("Full validation report config set mismatch")
    return by_config


def resolve_ground_truth_ranges(questions: list[dict], silver_records: list[dict]) -> dict[str, list[dict]]:
    silver_by_video = {record["video_id"]: record for record in silver_records}
    resolved = {}
    for question in questions:
        ranges = []
        for range_index, ground_truth in enumerate(question["relevant_time_ranges"], start=1):
            segments = silver_by_video[ground_truth["video_id"]]["segments"]
            start_matches = [
                segment["segment_index"]
                for segment in segments
                if abs(segment["start_second"] - ground_truth["start_second"]) < BOUNDARY_TOLERANCE
            ]
            end_matches = [
                segment["segment_index"]
                for segment in segments
                if abs((segment["start_second"] + segment["duration_second"]) - ground_truth["end_second"]) < BOUNDARY_TOLERANCE
            ]
            if len(start_matches) != 1 or len(end_matches) != 1:
                raise ValueError(f"Ground-truth boundary mapping is not unique: {question['question_id']} range {range_index}")
            if end_matches[0] < start_matches[0]:
                raise ValueError(f"Ground-truth segment range is reversed: {question['question_id']} range {range_index}")
            ranges.append({
                "range_index": range_index,
                "video_id": ground_truth["video_id"],
                "start_second": ground_truth["start_second"],
                "end_second": ground_truth["end_second"],
                "source_segment_start_index": start_matches[0],
                "source_segment_end_index": end_matches[0],
            })
        resolved[question["question_id"]] = ranges
    return resolved


def covered_range_indices(chunk: dict, ground_truth_ranges: list[dict]) -> list[int]:
    return [
        item["range_index"]
        for item in ground_truth_ranges
        if chunk["video_id"] == item["video_id"]
        and chunk["source_segment_start_index"] <= item["source_segment_end_index"]
        and chunk["source_segment_end_index"] >= item["source_segment_start_index"]
    ]


def serialize_csv(rows: list[dict]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")


def build_manifest(validation_rows: dict[str, dict], question_count: int, out_of_scope_count: int) -> dict:
    chunk_inputs = [
        {
            "chunking_config_id": config_id,
            "path": str(EXPERIMENT_ROOT / config_id / "chunks.jsonl").replace("\\", "/"),
            "sha256": validation_rows[config_id]["output_sha256"],
            "total_chunks": int(validation_rows[config_id]["total_chunks"]),
        }
        for config_id in CONFIG_IDS
    ]
    identity = {
        "retrieval_version": RETRIEVAL_VERSION,
        "evaluation_sha256": sha256_file(EVALUATION_FILE),
        "silver_sha256": sha256_file(SILVER_FILE),
        "chunk_inputs": chunk_inputs,
        "model_repository": MODEL_NAME,
        "model_revision": MODEL_REVISION,
        "k_values": list(K_VALUES),
        "relevance_rule": "same_video_and_source_segment_interval_intersection",
        "boundary_tolerance": BOUNDARY_TOLERANCE,
    }
    run_id = f"mit60001_dense_{sha256_bytes(canonical_bytes(identity))[:16]}"
    return {
        "schema_version": "chunking_retrieval_run_v1",
        "retrieval_run_id": run_id,
        **identity,
        "evaluation_file": str(EVALUATION_FILE).replace("\\", "/"),
        "approved_answerable_question_count": question_count,
        "excluded_out_of_scope_question_count": out_of_scope_count,
        "query_and_chunk_normalize_embeddings": True,
        "similarity": "cosine_via_dot_product_of_l2_normalized_vectors",
        "ranking_tie_break": "score_desc_then_chunk_id_asc",
        "top_k_exported": max(K_VALUES),
        "manual_citation_judgment": "pending",
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
        "sentence_transformers_version": sentence_transformers.__version__,
    }


def main() -> None:
    torch.manual_seed(0)
    np.random.seed(0)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)

    evaluation_records = load_jsonl(EVALUATION_FILE)
    approved = [record for record in evaluation_records if record["review_status"] == "approved"]
    questions = sorted([record for record in approved if record["answerable"]], key=lambda item: item["question_id"])
    out_of_scope = [record for record in approved if not record["answerable"]]
    if len(approved) != 40 or len(questions) != 35 or len(out_of_scope) != 5:
        raise ValueError("Canonical evaluation totals must be 40 approved, 35 answerable, and 5 out-of-scope")

    silver_records = load_jsonl(SILVER_FILE)
    if len(silver_records) != 38:
        raise ValueError("Silver corpus must contain 38 videos")
    ground_truth_by_question = resolve_ground_truth_ranges(questions, silver_records)
    if sum(len(items) for items in ground_truth_by_question.values()) != 57:
        raise ValueError("Expected 57 ground-truth ranges")

    validation_rows = load_validation_rows()
    manifest = build_manifest(validation_rows, len(questions), len(out_of_scope))
    run_id = manifest["retrieval_run_id"]

    model = SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION, local_files_only=True)
    actual_revision = getattr(model._first_module().auto_model.config, "_commit_hash", None)
    if actual_revision != MODEL_REVISION:
        raise RuntimeError(f"Loaded encoder revision mismatch: {actual_revision}")
    query_embeddings = model.encode(
        [question["question"] for question in questions],
        batch_size=32,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    detail_rows = []
    comparison_rows = []
    for config_id in CONFIG_IDS:
        chunk_path = EXPERIMENT_ROOT / config_id / "chunks.jsonl"
        if sha256_file(chunk_path) != validation_rows[config_id]["output_sha256"]:
            raise ValueError(f"Chunk hash differs from full validation report: {config_id}")
        chunks = load_jsonl(chunk_path)
        chunk_embeddings = model.encode(
            [chunk["chunk_text"] for chunk in chunks],
            batch_size=32,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        scores_matrix = query_embeddings @ chunk_embeddings.T
        config_metrics = []
        for question_index, question in enumerate(questions):
            scores = scores_matrix[question_index]
            ranked_indices = sorted(range(len(chunks)), key=lambda index: (-float(scores[index]), chunks[index]["chunk_id"]))
            ground_truth_ranges = ground_truth_by_question[question["question_id"]]
            all_range_indices = {item["range_index"] for item in ground_truth_ranges}
            covered = set()
            first_relevant_rank = None
            chunks_to_full_coverage = None
            covered_by_rank = []
            for rank, chunk_index in enumerate(ranked_indices, start=1):
                chunk_coverage = covered_range_indices(chunks[chunk_index], ground_truth_ranges)
                covered.update(chunk_coverage)
                covered_by_rank.append(set(covered))
                if first_relevant_rank is None and chunk_coverage:
                    first_relevant_rank = rank
                if chunks_to_full_coverage is None and covered == all_range_indices:
                    chunks_to_full_coverage = rank
                if first_relevant_rank is not None and chunks_to_full_coverage is not None and rank >= max(K_VALUES):
                    break
            if first_relevant_rank is None or chunks_to_full_coverage is None:
                raise RuntimeError(f"Relevant evidence is unreachable: {config_id} {question['question_id']}")

            metrics = {
                "first_relevant_rank": first_relevant_rank,
                "reciprocal_rank": 1.0 / first_relevant_rank,
                "chunks_to_full_coverage": chunks_to_full_coverage,
            }
            for k in K_VALUES:
                covered_at_k = covered_by_rank[min(k, len(covered_by_rank)) - 1]
                metrics[f"recall_at_{k}"] = int(first_relevant_rank <= k)
                metrics[f"evidence_ranges_covered_at_{k}"] = len(covered_at_k)
                metrics[f"evidence_range_recall_at_{k}"] = len(covered_at_k) / len(all_range_indices)
                metrics[f"full_evidence_coverage_at_{k}"] = int(covered_at_k == all_range_indices)
            config_metrics.append(metrics)

            top_indices = ranked_indices[: max(K_VALUES)]
            top_chunks = [chunks[index] for index in top_indices]
            top_coverages = [covered_range_indices(chunk, ground_truth_ranges) for chunk in top_chunks]
            detail_row = {
                "retrieval_run_id": run_id,
                "chunking_config_id": config_id,
                "question_id": question["question_id"],
                "question": question["question"],
                "category": question["category"],
                "ground_truth_range_count": len(ground_truth_ranges),
                "ground_truth_video_ids_json": json.dumps(question["relevant_video_ids"], separators=(",", ":")),
                "corpus_chunk_count": len(chunks),
                "first_relevant_rank": first_relevant_rank,
                "reciprocal_rank": round(metrics["reciprocal_rank"], 9),
                "chunks_to_full_coverage": chunks_to_full_coverage,
            }
            for k in K_VALUES:
                detail_row[f"recall_at_{k}"] = metrics[f"recall_at_{k}"]
                detail_row[f"evidence_ranges_covered_at_{k}"] = metrics[f"evidence_ranges_covered_at_{k}"]
                detail_row[f"evidence_range_recall_at_{k}"] = round(metrics[f"evidence_range_recall_at_{k}"], 9)
                detail_row[f"full_evidence_coverage_at_{k}"] = metrics[f"full_evidence_coverage_at_{k}"]
            detail_row.update({
                "top_10_chunk_ids_json": json.dumps([chunk["chunk_id"] for chunk in top_chunks], ensure_ascii=False, separators=(",", ":")),
                "top_10_scores_json": json.dumps([round(float(scores[index]), 8) for index in top_indices], separators=(",", ":")),
                "top_10_video_ids_json": json.dumps([chunk["video_id"] for chunk in top_chunks], separators=(",", ":")),
                "top_10_start_seconds_json": json.dumps([chunk["start_second"] for chunk in top_chunks], separators=(",", ":")),
                "top_10_end_seconds_json": json.dumps([chunk["end_second"] for chunk in top_chunks], separators=(",", ":")),
                "top_10_relevant_flags_json": json.dumps([bool(items) for items in top_coverages], separators=(",", ":")),
                "top_10_covered_range_indices_json": json.dumps(top_coverages, separators=(",", ":")),
                "manual_judgment": "",
            })
            detail_rows.append(detail_row)

        comparison_row = {
            "retrieval_run_id": run_id,
            "chunking_config_id": config_id,
            "question_count": len(config_metrics),
            "ground_truth_range_count": sum(len(ground_truth_by_question[question["question_id"]]) for question in questions),
            "corpus_chunk_count": int(validation_rows[config_id]["total_chunks"]),
            "mrr": round(statistics.fmean(item["reciprocal_rank"] for item in config_metrics), 9),
            "mean_first_relevant_rank": round(statistics.fmean(item["first_relevant_rank"] for item in config_metrics), 6),
            "median_first_relevant_rank": statistics.median(item["first_relevant_rank"] for item in config_metrics),
            "mean_chunks_to_full_coverage": round(statistics.fmean(item["chunks_to_full_coverage"] for item in config_metrics), 6),
            "median_chunks_to_full_coverage": statistics.median(item["chunks_to_full_coverage"] for item in config_metrics),
        }
        for k in K_VALUES:
            comparison_row[f"recall_at_{k}"] = round(statistics.fmean(item[f"recall_at_{k}"] for item in config_metrics), 9)
            comparison_row[f"mean_evidence_range_recall_at_{k}"] = round(statistics.fmean(item[f"evidence_range_recall_at_{k}"] for item in config_metrics), 9)
            comparison_row[f"full_evidence_coverage_rate_at_{k}"] = round(statistics.fmean(item[f"full_evidence_coverage_at_{k}"] for item in config_metrics), 9)
        comparison_row["manual_citation_review_status"] = "pending"
        comparison_rows.append(comparison_row)

    write_atomic(RESULTS_FILE, serialize_csv(detail_rows))
    write_atomic(COMPARISON_FILE, serialize_csv(comparison_rows))
    write_atomic(MANIFEST_FILE, json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n")
    print(json.dumps({
        "retrieval_run_id": run_id,
        "detail_rows": len(detail_rows),
        "comparison": comparison_rows,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
