"""So sánh Dense, exact BM25 và equal-weight RRF trên MIT 6.0001.

File này chỉ tạo retrieval candidates và metrics. Nó không chọn configuration thắng,
không tạo Ground Truth và không gọi Cross-Encoder hoặc LLM.
"""

import csv
import hashlib
import io
import json
import math
import platform
from pathlib import Path
import statistics

import numpy as np
import sentence_transformers
from sentence_transformers import SentenceTransformer
import torch
import transformers

from build_mit_60001_lexical_index import BM25_B, BM25_K1, TOKENIZER_VERSION, tokenize


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CANONICAL_GOLD_FILE = Path("data/gold/mit_60001/chunks.jsonl")
DENSE_EMBEDDINGS_FILE = Path("data/indexes/mit_60001/embeddings.npy")
DENSE_MANIFEST_FILE = Path("reports/09_embedding/embedding_index_manifest.json")
LEXICAL_INDEX_FILE = Path("data/indexes/mit_60001/lexical_index.json")
LEXICAL_MANIFEST_FILE = Path("reports/10_retrieval/lexical_index_manifest.json")
EVALUATION_FILE = Path("evaluation/mit_60001/evaluation_questions.jsonl")
SILVER_FILE = Path("data/silver/mit_60001/transcripts_clean.jsonl")
DENSE_BASELINE_DETAIL_FILE = Path("reports/09_embedding/production_index_retrieval_results.csv")
DENSE_BASELINE_COMPARISON_FILE = Path("reports/09_embedding/production_index_retrieval_comparison.csv")
RESULTS_FILE = Path("reports/10_retrieval/hybrid_retrieval_results.csv")
COMPARISON_FILE = Path("reports/10_retrieval/hybrid_retrieval_comparison.csv")
QUESTION_COMPARISON_FILE = Path("reports/10_retrieval/hybrid_retrieval_question_comparison.csv")
RUN_MANIFEST_FILE = Path("reports/10_retrieval/hybrid_retrieval_manifest.json")

MODEL_REPOSITORY = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
METHODS = ("dense_baseline_v1", "bm25_v1", "hybrid_rrf_k60_d100_v1")
K_VALUES = (1, 3, 5, 10)
RRF_CONSTANT = 60
RRF_DEPTH = 100
BOUNDARY_TOLERANCE = 1e-6
RETRIEVAL_VERSION = "mit60001_hybrid_retrieval_v1"
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


def canonical_json_bytes(value: object) -> bytes:
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
            if end_matches[0] < start_matches[0]:
                raise ValueError(f"Ground-truth range is reversed: {question['question_id']}")
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


def validated_inputs() -> tuple[list[dict], np.ndarray, dict, dict, dict]:
    """Xác minh Dense/lexical indexes cùng hash và document order với Gold."""

    chunks = load_jsonl(CANONICAL_GOLD_FILE)
    dense_manifest = json.loads(DENSE_MANIFEST_FILE.read_text(encoding="utf-8"))
    lexical_manifest = json.loads(LEXICAL_MANIFEST_FILE.read_text(encoding="utf-8"))
    lexical_index = json.loads(LEXICAL_INDEX_FILE.read_text(encoding="utf-8"))
    canonical_hash = sha256_file(CANONICAL_GOLD_FILE)
    if canonical_hash != dense_manifest["canonical_gold_sha256"]:
        raise ValueError("Canonical Gold differs from dense manifest")
    if canonical_hash != lexical_manifest["canonical_gold_sha256"]:
        raise ValueError("Canonical Gold differs from lexical manifest")
    if sha256_file(DENSE_EMBEDDINGS_FILE) != dense_manifest["embeddings_sha256"]:
        raise ValueError("Dense embeddings differ from dense manifest")
    if sha256_file(LEXICAL_INDEX_FILE) != lexical_manifest["lexical_index_sha256"]:
        raise ValueError("Lexical index differs from lexical manifest")
    if dense_manifest["chunk_id_order_sha256"] != lexical_manifest["chunk_id_order_sha256"]:
        raise ValueError("Dense and lexical document orders differ")
    if dense_manifest["validation_status"] != "passed" or lexical_manifest["validation_status"] != "passed":
        raise ValueError("Dense or lexical index is not passed")

    vectors = np.load(DENSE_EMBEDDINGS_FILE, allow_pickle=False)
    if vectors.shape != (861, 384) or vectors.dtype != np.float32:
        raise ValueError(f"Unexpected dense array: {vectors.shape} {vectors.dtype}")
    documents = lexical_index["documents"]
    if len(chunks) != 861 or len(documents) != 861:
        raise ValueError("Expected 861 Gold chunks and lexical documents")
    for position, (chunk, document) in enumerate(zip(chunks, documents, strict=True)):
        if document["index_position"] != position or document["chunk_id"] != chunk["chunk_id"]:
            raise ValueError(f"Lexical document order mismatch at position {position}")
    if lexical_index["tokenizer_version"] != TOKENIZER_VERSION:
        raise ValueError("Lexical tokenizer version mismatch")
    if lexical_index["bm25_k1"] != BM25_K1 or lexical_index["bm25_b"] != BM25_B:
        raise ValueError("BM25 parameters mismatch")
    return chunks, vectors, lexical_index, dense_manifest, lexical_manifest


def bm25_scores(query: str, lexical_index: dict) -> np.ndarray:
    """Tính exact BM25 bằng postings và unique query tokens."""

    count = lexical_index["chunk_count"]
    scores = np.zeros(count, dtype=np.float64)
    document_lengths = np.asarray(
        [item["document_length"] for item in lexical_index["documents"]],
        dtype=np.float64,
    )
    average_length = float(lexical_index["average_document_length"])
    postings_by_token = {item["token"]: item for item in lexical_index["postings"]}
    for token in sorted(set(tokenize(query))):
        posting_record = postings_by_token.get(token)
        if posting_record is None:
            continue
        document_frequency = posting_record["document_frequency"]
        inverse_document_frequency = math.log(
            1.0 + (count - document_frequency + 0.5) / (document_frequency + 0.5)
        )
        for document_position, term_frequency in posting_record["postings"]:
            normalization = BM25_K1 * (
                1.0 - BM25_B + BM25_B * document_lengths[document_position] / average_length
            )
            scores[document_position] += inverse_document_frequency * (
                term_frequency * (BM25_K1 + 1.0) / (term_frequency + normalization)
            )
    return scores


def ranked_indices(scores: np.ndarray, chunks: list[dict]) -> list[int]:
    return sorted(
        range(len(chunks)),
        key=lambda index: (-float(scores[index]), chunks[index]["chunk_id"]),
    )


def rrf_scores(dense_ranking: list[int], lexical_ranking: list[int], count: int) -> np.ndarray:
    scores = np.zeros(count, dtype=np.float64)
    for ranking in (dense_ranking, lexical_ranking):
        for rank, document_position in enumerate(ranking[:RRF_DEPTH], start=1):
            scores[document_position] += 1.0 / (RRF_CONSTANT + rank)
    return scores


def question_metrics(ranking: list[int], chunks: list[dict], ranges: list[dict]) -> dict:
    all_range_indices = {item["range_index"] for item in ranges}
    covered = set()
    covered_by_rank = []
    first_relevant_rank = None
    chunks_to_full_coverage = None
    for rank, chunk_index in enumerate(ranking, start=1):
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
        raise RuntimeError("Relevant evidence is unreachable")
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
    return metrics


def aggregate_metrics(method: str, run_id: str, question_rows: list[dict], range_count: int) -> dict:
    row = {
        "retrieval_run_id": run_id,
        "retrieval_method": method,
        "question_count": len(question_rows),
        "ground_truth_range_count": range_count,
        "corpus_chunk_count": 861,
        "mrr": round(statistics.fmean(item["reciprocal_rank"] for item in question_rows), 9),
        "mean_first_relevant_rank": round(
            statistics.fmean(item["first_relevant_rank"] for item in question_rows), 6
        ),
        "median_first_relevant_rank": statistics.median(
            item["first_relevant_rank"] for item in question_rows
        ),
        "mean_chunks_to_full_coverage": round(
            statistics.fmean(item["chunks_to_full_coverage"] for item in question_rows), 6
        ),
        "median_chunks_to_full_coverage": statistics.median(
            item["chunks_to_full_coverage"] for item in question_rows
        ),
    }
    for k in K_VALUES:
        row[f"recall_at_{k}"] = round(
            statistics.fmean(item[f"recall_at_{k}"] for item in question_rows), 9
        )
        row[f"mean_evidence_range_recall_at_{k}"] = round(
            statistics.fmean(item[f"evidence_range_recall_at_{k}"] for item in question_rows), 9
        )
        row[f"full_evidence_coverage_rate_at_{k}"] = round(
            statistics.fmean(item[f"full_evidence_coverage_at_{k}"] for item in question_rows), 9
        )
    row["selection_status"] = "pending_human_decision"
    return row


def main() -> None:
    torch.manual_seed(0)
    np.random.seed(0)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)

    chunks, dense_vectors, lexical_index, dense_manifest, lexical_manifest = validated_inputs()
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
    ground_truth = resolve_ground_truth_ranges(questions, silver_records)
    ground_truth_range_count = sum(len(ranges) for ranges in ground_truth.values())
    if len(silver_records) != 38 or ground_truth_range_count != 57:
        raise ValueError("Expected 38 Silver videos and 57 Ground Truth ranges")

    model = SentenceTransformer(
        MODEL_REPOSITORY,
        revision=MODEL_REVISION,
        local_files_only=True,
        device="cpu",
    )
    actual_revision = getattr(model._first_module().auto_model.config, "_commit_hash", None)
    if actual_revision != MODEL_REVISION or model.get_embedding_dimension() != 384:
        raise RuntimeError("Query encoder differs from dense index contract")
    query_vectors = model.encode(
        [question["question"] for question in questions],
        batch_size=32,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    query_vectors = np.asarray(query_vectors, dtype=np.float32, order="C")
    dense_scores_matrix = query_vectors @ dense_vectors.T

    identity = {
        "retrieval_version": RETRIEVAL_VERSION,
        "evaluation_sha256": sha256_file(EVALUATION_FILE),
        "dense_index_content_sha256": dense_manifest["index_content_sha256"],
        "lexical_index_sha256": lexical_manifest["lexical_index_sha256"],
        "methods": list(METHODS),
        "rrf_constant": RRF_CONSTANT,
        "rrf_depth": RRF_DEPTH,
    }
    retrieval_run_id = f"mit60001_hybrid_{sha256_bytes(canonical_json_bytes(identity))[:16]}"
    baseline_details = {row["question_id"]: row for row in load_csv(DENSE_BASELINE_DETAIL_FILE)}
    baseline_comparison_rows = load_csv(DENSE_BASELINE_COMPARISON_FILE)
    if len(baseline_details) != 35 or len(baseline_comparison_rows) != 1:
        raise ValueError("Dense production baseline artifacts have unexpected row counts")
    baseline_comparison = baseline_comparison_rows[0]

    details = []
    metrics_by_method = {method: [] for method in METHODS}
    top_ids_by_method = {method: [] for method in METHODS}
    dense_top_10_id_match_count = 0
    dense_top_10_score_match_count = 0
    for question_index, question in enumerate(questions):
        dense_scores = dense_scores_matrix[question_index]
        lexical_scores = bm25_scores(question["question"], lexical_index)
        dense_ranking = ranked_indices(dense_scores, chunks)
        lexical_ranking = ranked_indices(lexical_scores, chunks)
        hybrid_scores = rrf_scores(dense_ranking, lexical_ranking, len(chunks))
        hybrid_ranking = ranked_indices(hybrid_scores, chunks)
        methods = {
            "dense_baseline_v1": (dense_scores, dense_ranking),
            "bm25_v1": (lexical_scores, lexical_ranking),
            "hybrid_rrf_k60_d100_v1": (hybrid_scores, hybrid_ranking),
        }
        ranges = ground_truth[question["question_id"]]
        for method in METHODS:
            scores, ranking = methods[method]
            metrics = question_metrics(ranking, chunks, ranges)
            metrics_by_method[method].append(metrics)
            top_indices = ranking[:max(K_VALUES)]
            top_ids = [chunks[index]["chunk_id"] for index in top_indices]
            top_scores = [round(float(scores[index]), 8) for index in top_indices]
            top_relevant = [bool(covered_range_indices(chunks[index], ranges)) for index in top_indices]
            top_ids_by_method[method].append(top_ids)
            details.append({
                "retrieval_run_id": retrieval_run_id,
                "retrieval_method": method,
                "question_id": question["question_id"],
                "first_relevant_rank": metrics["first_relevant_rank"],
                "reciprocal_rank": round(metrics["reciprocal_rank"], 9),
                "chunks_to_full_coverage": metrics["chunks_to_full_coverage"],
                "top_10_chunk_ids_json": json.dumps(top_ids, ensure_ascii=False, separators=(",", ":")),
                "top_10_scores_json": json.dumps(top_scores, separators=(",", ":")),
                "top_10_relevant_flags_json": json.dumps(top_relevant, separators=(",", ":")),
            })
            if method == "dense_baseline_v1":
                baseline = baseline_details[question["question_id"]]
                dense_top_10_id_match_count += int(
                    top_ids == json.loads(baseline["top_10_chunk_ids_json"])
                )
                dense_top_10_score_match_count += int(
                    top_scores == json.loads(baseline["top_10_scores_json"])
                )

    comparisons = [
        aggregate_metrics(
            method,
            retrieval_run_id,
            metrics_by_method[method],
            ground_truth_range_count,
        )
        for method in METHODS
    ]
    dense_comparison = comparisons[0]
    dense_baseline_metrics_match = all(
        abs(float(dense_comparison[field]) - float(baseline_comparison[field])) <= 1e-9
        for field in METRIC_FIELDS
    )
    if not dense_baseline_metrics_match or dense_top_10_id_match_count != 35 or dense_top_10_score_match_count != 35:
        raise RuntimeError(
            "Dense branch differs from locked production baseline: "
            f"metrics={dense_baseline_metrics_match}, ids={dense_top_10_id_match_count}/35, "
            f"scores={dense_top_10_score_match_count}/35"
        )

    question_comparisons = []
    for question_index, question in enumerate(questions):
        dense_metrics = metrics_by_method["dense_baseline_v1"][question_index]
        lexical_metrics = metrics_by_method["bm25_v1"][question_index]
        hybrid_metrics = metrics_by_method["hybrid_rrf_k60_d100_v1"][question_index]
        dense_ids = top_ids_by_method["dense_baseline_v1"][question_index]
        lexical_ids = top_ids_by_method["bm25_v1"][question_index]
        hybrid_ids = top_ids_by_method["hybrid_rrf_k60_d100_v1"][question_index]
        first_rank_delta = hybrid_metrics["first_relevant_rank"] - dense_metrics["first_relevant_rank"]
        if first_rank_delta < 0:
            first_rank_outcome = "improved"
        elif first_rank_delta > 0:
            first_rank_outcome = "worse"
        else:
            first_rank_outcome = "equal"
        question_comparisons.append({
            "retrieval_run_id": retrieval_run_id,
            "question_id": question["question_id"],
            "question": question["question"],
            "category": question["category"],
            "ground_truth_video_ids_json": json.dumps(
                question["relevant_video_ids"], separators=(",", ":")
            ),
            "dense_first_relevant_rank": dense_metrics["first_relevant_rank"],
            "bm25_first_relevant_rank": lexical_metrics["first_relevant_rank"],
            "hybrid_first_relevant_rank": hybrid_metrics["first_relevant_rank"],
            "hybrid_first_rank_delta_vs_dense": first_rank_delta,
            "hybrid_first_rank_outcome": first_rank_outcome,
            "dense_chunks_to_full_coverage": dense_metrics["chunks_to_full_coverage"],
            "bm25_chunks_to_full_coverage": lexical_metrics["chunks_to_full_coverage"],
            "hybrid_chunks_to_full_coverage": hybrid_metrics["chunks_to_full_coverage"],
            "hybrid_full_coverage_rank_delta_vs_dense": (
                hybrid_metrics["chunks_to_full_coverage"]
                - dense_metrics["chunks_to_full_coverage"]
            ),
            "dense_recall_at_10": dense_metrics["recall_at_10"],
            "bm25_recall_at_10": lexical_metrics["recall_at_10"],
            "hybrid_recall_at_10": hybrid_metrics["recall_at_10"],
            "hybrid_top_10_overlap_count_with_dense": len(set(dense_ids) & set(hybrid_ids)),
            "hybrid_top_10_new_count_vs_dense": len(set(hybrid_ids) - set(dense_ids)),
            "dense_top_10_chunk_ids_json": json.dumps(dense_ids, ensure_ascii=False, separators=(",", ":")),
            "bm25_top_10_chunk_ids_json": json.dumps(lexical_ids, ensure_ascii=False, separators=(",", ":")),
            "hybrid_top_10_chunk_ids_json": json.dumps(hybrid_ids, ensure_ascii=False, separators=(",", ":")),
            "review_status": "pending_human_decision",
        })

    details_bytes = serialize_csv(details)
    comparisons_bytes = serialize_csv(comparisons)
    question_comparisons_bytes = serialize_csv(question_comparisons)
    manifest = {
        "schema_version": "hybrid_retrieval_run_v1",
        "retrieval_run_id": retrieval_run_id,
        **identity,
        "canonical_gold_sha256": sha256_file(CANONICAL_GOLD_FILE),
        "dense_index_run_id": dense_manifest["index_run_id"],
        "dense_index_manifest_sha256": sha256_file(DENSE_MANIFEST_FILE),
        "lexical_index_run_id": lexical_manifest["index_run_id"],
        "lexical_index_manifest_sha256": sha256_file(LEXICAL_MANIFEST_FILE),
        "tokenizer_version": TOKENIZER_VERSION,
        "bm25_k1": BM25_K1,
        "bm25_b": BM25_B,
        "query_unique_tokens": True,
        "rrf_dense_weight": 1,
        "rrf_lexical_weight": 1,
        "model_repository": MODEL_REPOSITORY,
        "model_revision": MODEL_REVISION,
        "query_normalize_embeddings": True,
        "ranking_tie_break": "score_desc_then_chunk_id_asc",
        "approved_answerable_question_count": len(questions),
        "excluded_out_of_scope_question_count": len(out_of_scope),
        "ground_truth_range_count": ground_truth_range_count,
        "relevance_rule": "same_video_and_source_segment_interval_intersection",
        "dense_baseline_detail_sha256": sha256_file(DENSE_BASELINE_DETAIL_FILE),
        "dense_baseline_comparison_sha256": sha256_file(DENSE_BASELINE_COMPARISON_FILE),
        "dense_baseline_metrics_match": dense_baseline_metrics_match,
        "dense_top_10_id_match_count": dense_top_10_id_match_count,
        "dense_top_10_score_match_count": dense_top_10_score_match_count,
        "results_sha256": sha256_bytes(details_bytes),
        "comparison_sha256": sha256_bytes(comparisons_bytes),
        "question_comparison_sha256": sha256_bytes(question_comparisons_bytes),
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
        "sentence_transformers_version": sentence_transformers.__version__,
        "selection_status": "pending_human_decision",
        "validation_status": "passed",
    }
    write_atomic(RESULTS_FILE, details_bytes)
    write_atomic(COMPARISON_FILE, comparisons_bytes)
    write_atomic(QUESTION_COMPARISON_FILE, question_comparisons_bytes)
    write_atomic(
        RUN_MANIFEST_FILE,
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n",
    )
    print(json.dumps({
        "retrieval_run_id": retrieval_run_id,
        "comparison": comparisons,
        "dense_baseline_metrics_match": dense_baseline_metrics_match,
        "dense_top_10_id_match_count": dense_top_10_id_match_count,
        "dense_top_10_score_match_count": dense_top_10_score_match_count,
        "selection_status": "pending_human_decision",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
