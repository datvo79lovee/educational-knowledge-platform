"""Đánh giá production dense index bằng 35 canonical answerable questions.

Kết quả phải khớp dense baseline của selected chunk configuration ở cả metrics tổng
hợp lẫn Top 10 chunk IDs/scores cho từng câu. Report không chứa chunk text.
"""

import csv
import hashlib
import io
import json
import platform
from pathlib import Path
import statistics

import numpy as np
import sentence_transformers
from sentence_transformers import SentenceTransformer
import torch
import transformers


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INDEX_MANIFEST_FILE = Path("reports/09_embedding/embedding_index_manifest.json")
CANONICAL_GOLD_FILE = Path("data/gold/mit_60001/chunks.jsonl")
EMBEDDINGS_FILE = Path("data/indexes/mit_60001/embeddings.npy")
METADATA_FILE = Path("data/indexes/mit_60001/metadata.jsonl")
EVALUATION_FILE = Path("evaluation/mit_60001/evaluation_questions.jsonl")
SILVER_FILE = Path("data/silver/mit_60001/transcripts_clean.jsonl")
BASELINE_DETAIL_FILE = Path("reports/08_chunking/chunking_retrieval_results.csv")
BASELINE_COMPARISON_FILE = Path("reports/08_chunking/chunking_comparison.csv")
RESULTS_FILE = Path("reports/09_embedding/production_index_retrieval_results.csv")
COMPARISON_FILE = Path("reports/09_embedding/production_index_retrieval_comparison.csv")
RUN_MANIFEST_FILE = Path("reports/09_embedding/production_index_retrieval_manifest.json")

MODEL_REPOSITORY = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
CONFIG_ID = "semantic_cosine_wp240_v1"
K_VALUES = (1, 3, 5, 10)
BOUNDARY_TOLERANCE = 1e-6
METRIC_FIELDS = (
    "mrr",
    "mean_first_relevant_rank",
    "median_first_relevant_rank",
    "mean_chunks_to_full_coverage",
    "median_chunks_to_full_coverage",
    "recall_at_1",
    "mean_evidence_range_recall_at_1",
    "full_evidence_coverage_rate_at_1",
    "recall_at_3",
    "mean_evidence_range_recall_at_3",
    "full_evidence_coverage_rate_at_3",
    "recall_at_5",
    "mean_evidence_range_recall_at_5",
    "full_evidence_coverage_rate_at_5",
    "recall_at_10",
    "mean_evidence_range_recall_at_10",
    "full_evidence_coverage_rate_at_10",
)


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_bytes(content)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def serialize_csv(rows: list[dict]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")


def resolve_ground_truth_ranges(questions: list[dict], silver_records: list[dict]) -> dict[str, list[dict]]:
    """Map timestamp Ground Truth về Silver segment interval như baseline."""

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
                if abs(
                    segment["start_second"]
                    + segment["duration_second"]
                    - ground_truth["end_second"]
                ) < BOUNDARY_TOLERANCE
            ]
            if len(start_matches) != 1 or len(end_matches) != 1:
                raise ValueError(
                    f"Ground-truth boundary mapping is not unique: "
                    f"{question['question_id']} range {range_index}"
                )
            ranges.append({
                "range_index": range_index,
                "video_id": ground_truth["video_id"],
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


def validated_index() -> tuple[dict, list[dict], np.ndarray]:
    """Xác minh hash, shape, metadata order và vector invariants trước retrieval."""

    manifest = json.loads(INDEX_MANIFEST_FILE.read_text(encoding="utf-8"))
    if manifest["validation_status"] != "passed":
        raise ValueError("Production index manifest is not passed")
    if sha256_file(CANONICAL_GOLD_FILE) != manifest["canonical_gold_sha256"]:
        raise ValueError("Canonical Gold hash differs from index manifest")
    if sha256_file(EMBEDDINGS_FILE) != manifest["embeddings_sha256"]:
        raise ValueError("Embedding file hash differs from index manifest")
    if sha256_file(METADATA_FILE) != manifest["metadata_sha256"]:
        raise ValueError("Metadata file hash differs from index manifest")

    chunks = load_jsonl(CANONICAL_GOLD_FILE)
    metadata = load_jsonl(METADATA_FILE)
    vectors = np.load(EMBEDDINGS_FILE, allow_pickle=False)
    if vectors.shape != (861, 384) or vectors.dtype != np.float32:
        raise ValueError(f"Unexpected production embedding array: {vectors.shape} {vectors.dtype}")
    if not np.isfinite(vectors).all():
        raise ValueError("Production index contains non-finite values")
    if int((np.abs(np.linalg.norm(vectors, axis=1) - 1.0) > manifest["norm_tolerance"]).sum()):
        raise ValueError("Production index contains non-normalized vectors")
    if len(chunks) != len(metadata) or len(chunks) != vectors.shape[0]:
        raise ValueError("Chunk, metadata and vector counts differ")
    for position, (chunk, item) in enumerate(zip(chunks, metadata, strict=True)):
        if item["index_position"] != position or item["chunk_id"] != chunk["chunk_id"]:
            raise ValueError(f"Metadata order differs from canonical Gold at position {position}")
    return manifest, chunks, vectors


def main() -> None:
    """Chạy production retrieval, so baseline và ghi ba artifact audit."""

    torch.manual_seed(0)
    np.random.seed(0)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)

    index_manifest, chunks, vectors = validated_index()
    evaluation_records = load_jsonl(EVALUATION_FILE)
    approved = [record for record in evaluation_records if record["review_status"] == "approved"]
    questions = sorted(
        [record for record in approved if record["answerable"]],
        key=lambda record: record["question_id"],
    )
    out_of_scope = [record for record in approved if not record["answerable"]]
    if len(approved) != 40 or len(questions) != 35 or len(out_of_scope) != 5:
        raise ValueError("Expected 40 approved questions: 35 answerable and 5 out-of-scope")
    silver_records = load_jsonl(SILVER_FILE)
    if len(silver_records) != 38:
        raise ValueError("Expected 38 Silver videos")
    ground_truth = resolve_ground_truth_ranges(questions, silver_records)
    if sum(len(ranges) for ranges in ground_truth.values()) != 57:
        raise ValueError("Expected 57 Ground Truth ranges")

    model = SentenceTransformer(
        MODEL_REPOSITORY,
        revision=MODEL_REVISION,
        local_files_only=True,
        device="cpu",
    )
    actual_revision = getattr(model._first_module().auto_model.config, "_commit_hash", None)
    if actual_revision != MODEL_REVISION or model.get_embedding_dimension() != 384:
        raise RuntimeError("Production query encoder differs from index encoder contract")
    query_vectors = model.encode(
        [question["question"] for question in questions],
        batch_size=32,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    query_vectors = np.asarray(query_vectors, dtype=np.float32, order="C")
    scores_matrix = query_vectors @ vectors.T

    baseline_details = {
        row["question_id"]: row
        for row in load_csv(BASELINE_DETAIL_FILE)
        if row["chunking_config_id"] == CONFIG_ID
    }
    baseline_rows = [
        row for row in load_csv(BASELINE_COMPARISON_FILE)
        if row["chunking_config_id"] == CONFIG_ID
    ]
    if len(baseline_details) != 35 or len(baseline_rows) != 1:
        raise ValueError("Selected-config baseline must contain 35 details and one comparison row")
    baseline = baseline_rows[0]

    identity = {
        "index_run_id": index_manifest["index_run_id"],
        "index_content_sha256": index_manifest["index_content_sha256"],
        "evaluation_sha256": sha256_file(EVALUATION_FILE),
        "model_revision": MODEL_REVISION,
        "baseline_comparison_sha256": sha256_file(BASELINE_COMPARISON_FILE),
    }
    retrieval_run_id = f"mit60001_production_{sha256_bytes(canonical_bytes(identity))[:16]}"
    result_rows = []
    question_metrics = []
    top_10_id_match_count = 0
    top_10_score_match_count = 0

    for question_index, question in enumerate(questions):
        scores = scores_matrix[question_index]
        ranked_indices = sorted(
            range(len(chunks)),
            key=lambda index: (-float(scores[index]), chunks[index]["chunk_id"]),
        )
        ranges = ground_truth[question["question_id"]]
        all_range_indices = {item["range_index"] for item in ranges}
        covered = set()
        covered_by_rank = []
        first_relevant_rank = None
        chunks_to_full_coverage = None
        for rank, chunk_index in enumerate(ranked_indices, start=1):
            chunk_coverage = covered_range_indices(chunks[chunk_index], ranges)
            covered.update(chunk_coverage)
            covered_by_rank.append(set(covered))
            if first_relevant_rank is None and chunk_coverage:
                first_relevant_rank = rank
            if chunks_to_full_coverage is None and covered == all_range_indices:
                chunks_to_full_coverage = rank
            if first_relevant_rank is not None and chunks_to_full_coverage is not None and rank >= max(K_VALUES):
                break
        if first_relevant_rank is None or chunks_to_full_coverage is None:
            raise RuntimeError(f"Relevant evidence is unreachable: {question['question_id']}")

        metrics = {
            "first_relevant_rank": first_relevant_rank,
            "reciprocal_rank": 1.0 / first_relevant_rank,
            "chunks_to_full_coverage": chunks_to_full_coverage,
        }
        for k in K_VALUES:
            covered_at_k = covered_by_rank[min(k, len(covered_by_rank)) - 1]
            metrics[f"recall_at_{k}"] = int(first_relevant_rank <= k)
            metrics[f"evidence_range_recall_at_{k}"] = len(covered_at_k) / len(all_range_indices)
            metrics[f"full_evidence_coverage_at_{k}"] = int(covered_at_k == all_range_indices)
        question_metrics.append(metrics)

        top_indices = ranked_indices[:max(K_VALUES)]
        top_ids = [chunks[index]["chunk_id"] for index in top_indices]
        top_scores = [round(float(scores[index]), 8) for index in top_indices]
        baseline_detail = baseline_details[question["question_id"]]
        ids_match = top_ids == json.loads(baseline_detail["top_10_chunk_ids_json"])
        scores_match = top_scores == json.loads(baseline_detail["top_10_scores_json"])
        top_10_id_match_count += int(ids_match)
        top_10_score_match_count += int(scores_match)
        result_rows.append({
            "retrieval_run_id": retrieval_run_id,
            "index_run_id": index_manifest["index_run_id"],
            "question_id": question["question_id"],
            "first_relevant_rank": first_relevant_rank,
            "chunks_to_full_coverage": chunks_to_full_coverage,
            "top_10_chunk_ids_json": json.dumps(top_ids, ensure_ascii=False, separators=(",", ":")),
            "top_10_scores_json": json.dumps(top_scores, separators=(",", ":")),
            "baseline_top_10_chunk_ids_match": ids_match,
            "baseline_top_10_scores_match": scores_match,
        })

    comparison = {
        "retrieval_run_id": retrieval_run_id,
        "index_run_id": index_manifest["index_run_id"],
        "baseline_retrieval_run_id": baseline["retrieval_run_id"],
        "question_count": len(question_metrics),
        "ground_truth_range_count": sum(len(ranges) for ranges in ground_truth.values()),
        "corpus_chunk_count": len(chunks),
        "mrr": round(statistics.fmean(item["reciprocal_rank"] for item in question_metrics), 9),
        "mean_first_relevant_rank": round(statistics.fmean(item["first_relevant_rank"] for item in question_metrics), 6),
        "median_first_relevant_rank": statistics.median(item["first_relevant_rank"] for item in question_metrics),
        "mean_chunks_to_full_coverage": round(statistics.fmean(item["chunks_to_full_coverage"] for item in question_metrics), 6),
        "median_chunks_to_full_coverage": statistics.median(item["chunks_to_full_coverage"] for item in question_metrics),
    }
    for k in K_VALUES:
        comparison[f"recall_at_{k}"] = round(
            statistics.fmean(item[f"recall_at_{k}"] for item in question_metrics), 9
        )
        comparison[f"mean_evidence_range_recall_at_{k}"] = round(
            statistics.fmean(item[f"evidence_range_recall_at_{k}"] for item in question_metrics), 9
        )
        comparison[f"full_evidence_coverage_rate_at_{k}"] = round(
            statistics.fmean(item[f"full_evidence_coverage_at_{k}"] for item in question_metrics), 9
        )

    metric_differences = {
        field: round(float(comparison[field]) - float(baseline[field]), 12)
        for field in METRIC_FIELDS
    }
    baseline_metrics_match = all(abs(value) <= 1e-9 for value in metric_differences.values())
    comparison.update({
        "baseline_metrics_match": baseline_metrics_match,
        "top_10_chunk_id_match_count": top_10_id_match_count,
        "top_10_score_match_count": top_10_score_match_count,
        "validation_status": "passed"
        if baseline_metrics_match and top_10_id_match_count == 35 and top_10_score_match_count == 35
        else "failed",
    })
    if comparison["validation_status"] != "passed":
        raise RuntimeError(
            "Production retrieval differs from baseline: "
            f"metrics={baseline_metrics_match}, ids={top_10_id_match_count}/35, "
            f"scores={top_10_score_match_count}/35"
        )

    results_bytes = serialize_csv(result_rows)
    comparison_bytes = serialize_csv([comparison])
    run_manifest = {
        "schema_version": "production_index_retrieval_run_v1",
        "retrieval_run_id": retrieval_run_id,
        **identity,
        "index_manifest_file": str(INDEX_MANIFEST_FILE).replace("\\", "/"),
        "index_manifest_sha256": sha256_file(INDEX_MANIFEST_FILE),
        "evaluation_file": str(EVALUATION_FILE).replace("\\", "/"),
        "approved_answerable_question_count": len(questions),
        "excluded_out_of_scope_question_count": len(out_of_scope),
        "ground_truth_range_count": sum(len(ranges) for ranges in ground_truth.values()),
        "model_repository": MODEL_REPOSITORY,
        "query_normalize_embeddings": True,
        "similarity": "cosine_via_dot_product_of_l2_normalized_vectors",
        "ranking_tie_break": "score_desc_then_chunk_id_asc",
        "k_values": list(K_VALUES),
        "relevance_rule": "same_video_and_source_segment_interval_intersection",
        "baseline_detail_file": str(BASELINE_DETAIL_FILE).replace("\\", "/"),
        "baseline_detail_sha256": sha256_file(BASELINE_DETAIL_FILE),
        "baseline_comparison_file": str(BASELINE_COMPARISON_FILE).replace("\\", "/"),
        "results_sha256": sha256_bytes(results_bytes),
        "comparison_sha256": sha256_bytes(comparison_bytes),
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
        "sentence_transformers_version": sentence_transformers.__version__,
        "baseline_metrics_match": baseline_metrics_match,
        "top_10_chunk_id_match_count": top_10_id_match_count,
        "top_10_score_match_count": top_10_score_match_count,
        "validation_status": comparison["validation_status"],
    }
    write_atomic(RESULTS_FILE, results_bytes)
    write_atomic(COMPARISON_FILE, comparison_bytes)
    write_atomic(
        RUN_MANIFEST_FILE,
        json.dumps(run_manifest, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n",
    )
    print(json.dumps(comparison, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
