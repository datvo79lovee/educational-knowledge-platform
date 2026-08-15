"""Rerank Dense Top 50 candidates bằng Cross-Encoder đã khóa revision.

Script chỉ đánh giá 35 canonical answerable questions. Nó không sửa Ground Truth,
không chọn reranker thắng và không gọi LLM. Model được cache trong data/models/, là
generated data đã gitignore. Lần tải đầu tiên phải truyền --allow-model-download;
các lần sau mặc định chỉ dùng local cache.
"""

import argparse
import hashlib
import json
import platform
from pathlib import Path

import jsonschema
import numpy as np
import sentence_transformers
from sentence_transformers import CrossEncoder, SentenceTransformer
import torch
import transformers

from evaluate_hybrid_retrieval import (
    METRIC_FIELDS,
    aggregate_metrics,
    canonical_json_bytes,
    covered_range_indices,
    load_csv,
    load_jsonl,
    question_metrics,
    resolve_ground_truth_ranges,
    serialize_csv,
    sha256_bytes,
    sha256_file,
    write_atomic,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CANONICAL_GOLD_FILE = PROJECT_ROOT / "data/gold/mit_60001/chunks.jsonl"
DENSE_EMBEDDINGS_FILE = PROJECT_ROOT / "data/indexes/mit_60001/embeddings.npy"
DENSE_METADATA_FILE = PROJECT_ROOT / "data/indexes/mit_60001/metadata.jsonl"
DENSE_MANIFEST_FILE = PROJECT_ROOT / "reports/09_embedding/embedding_index_manifest.json"
EVALUATION_FILE = PROJECT_ROOT / "evaluation/mit_60001/evaluation_questions.jsonl"
SILVER_FILE = PROJECT_ROOT / "data/silver/mit_60001/transcripts_clean.jsonl"
RETRIEVAL_DECISION_FILE = (
    PROJECT_ROOT / "reports/10_retrieval/retrieval_configuration_decision_2026-08-14.csv"
)
DENSE_BASELINE_RESULTS_FILE = (
    PROJECT_ROOT / "reports/10_retrieval/hybrid_retrieval_results.csv"
)
DENSE_BASELINE_COMPARISON_FILE = (
    PROJECT_ROOT / "reports/10_retrieval/hybrid_retrieval_comparison.csv"
)
SCHEMA_FILE = PROJECT_ROOT / "schemas/cross_encoder_reranking_manifest_v1.schema.json"
MODEL_CACHE_FOLDER = PROJECT_ROOT / "data/models/huggingface"
REPORT_FOLDER = PROJECT_ROOT / "reports/11_reranking"
RESULTS_FILE = REPORT_FOLDER / "cross_encoder_reranking_results.csv"
COMPARISON_FILE = REPORT_FOLDER / "cross_encoder_reranking_comparison.csv"
QUESTION_COMPARISON_FILE = REPORT_FOLDER / "cross_encoder_reranking_question_comparison.csv"
VALIDATION_FILE = REPORT_FOLDER / "cross_encoder_reranking_validation.csv"
MANIFEST_FILE = REPORT_FOLDER / "cross_encoder_reranking_manifest.json"

DENSE_MODEL_REPOSITORY = "sentence-transformers/all-MiniLM-L6-v2"
DENSE_MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
RERANKER_MODEL_REPOSITORY = "cross-encoder/ms-marco-MiniLM-L6-v2"
RERANKER_MODEL_REVISION = "c5ee24cb16019beea0893ab7796b1df96625c6b8"
RERANKER_MODEL_WEIGHTS_SHA256 = (
    "821d1aa69520101d6e0737f78a042ae25b19e5cb9160701909d10434f4aeb0ae"
)
RERANKING_VERSION = "mit60001_cross_encoder_reranking_v1"
SELECTED_RETRIEVAL_METHOD = "dense_baseline_v1"
RERANKED_METHOD = "cross_encoder_ms_marco_minilm_l6_v2"
CANDIDATE_DEPTH = 50
OUTPUT_TOP_K = 3
MAX_LENGTH = 512
BATCH_SIZE = 16
K_VALUES = (1, 3, 5, 10)


def project_relative(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-model-download",
        action="store_true",
        help="Cho phép tải pinned Cross-Encoder vào data/models/ ở lần chạy đầu.",
    )
    parser.add_argument(
        "--output-folder",
        type=Path,
        help="Ghi physical outputs vào folder khác nhưng giữ canonical paths trong manifest.",
    )
    return parser.parse_args()


def validate_static_inputs() -> tuple[dict, list[dict], np.ndarray, list[dict], list[dict], dict]:
    """Khóa hash, document order, benchmark và Dense selection trước khi infer."""

    dense_manifest = json.loads(DENSE_MANIFEST_FILE.read_text(encoding="utf-8"))
    chunks = load_jsonl(CANONICAL_GOLD_FILE)
    metadata = load_jsonl(DENSE_METADATA_FILE)
    vectors = np.load(DENSE_EMBEDDINGS_FILE, allow_pickle=False)
    if dense_manifest["validation_status"] != "passed":
        raise ValueError("Dense index manifest is not passed")
    if sha256_file(CANONICAL_GOLD_FILE) != dense_manifest["canonical_gold_sha256"]:
        raise ValueError("Canonical Gold differs from Dense manifest")
    if sha256_file(DENSE_EMBEDDINGS_FILE) != dense_manifest["embeddings_sha256"]:
        raise ValueError("Dense embeddings differ from Dense manifest")
    if sha256_file(DENSE_METADATA_FILE) != dense_manifest["metadata_sha256"]:
        raise ValueError("Dense metadata differs from Dense manifest")
    if len(chunks) != 861 or len(metadata) != 861 or vectors.shape != (861, 384):
        raise ValueError("Expected 861 chunks and a 861 x 384 Dense index")
    if vectors.dtype != np.float32 or not np.isfinite(vectors).all():
        raise ValueError("Dense vectors must be finite float32")
    for position, (chunk, item) in enumerate(zip(chunks, metadata, strict=True)):
        if item["index_position"] != position or item["chunk_id"] != chunk["chunk_id"]:
            raise ValueError(f"Dense metadata order mismatch at position {position}")

    decisions = load_csv(RETRIEVAL_DECISION_FILE)
    selected = [row for row in decisions if row["selection_status"] == "selected"]
    if len(selected) != 1 or selected[0]["retrieval_method"] != SELECTED_RETRIEVAL_METHOD:
        raise ValueError("Retrieval decision does not select exactly dense_baseline_v1")

    approved = [
        record
        for record in load_jsonl(EVALUATION_FILE)
        if record["review_status"] == "approved"
    ]
    questions = sorted(
        [record for record in approved if record["answerable"]],
        key=lambda record: record["question_id"],
    )
    out_of_scope = [record for record in approved if not record["answerable"]]
    if len(approved) != 40 or len(questions) != 35 or len(out_of_scope) != 5:
        raise ValueError("Expected 40 approved questions: 35 answerable and 5 out-of-scope")
    silver_records = load_jsonl(SILVER_FILE)
    ground_truth = resolve_ground_truth_ranges(questions, silver_records)
    if len(silver_records) != 38 or sum(map(len, ground_truth.values())) != 57:
        raise ValueError("Expected 38 Silver videos and 57 Ground Truth ranges")
    return dense_manifest, chunks, vectors, questions, out_of_scope, ground_truth


def load_dense_query_model() -> SentenceTransformer:
    model = SentenceTransformer(
        DENSE_MODEL_REPOSITORY,
        revision=DENSE_MODEL_REVISION,
        local_files_only=True,
        device="cpu",
    )
    actual_revision = getattr(model._first_module().auto_model.config, "_commit_hash", None)
    if actual_revision != DENSE_MODEL_REVISION or model.get_embedding_dimension() != 384:
        raise RuntimeError("Dense query encoder differs from locked index contract")
    return model


def load_reranker(allow_download: bool) -> CrossEncoder:
    MODEL_CACHE_FOLDER.mkdir(parents=True, exist_ok=True)
    model = CrossEncoder(
        RERANKER_MODEL_REPOSITORY,
        revision=RERANKER_MODEL_REVISION,
        cache_folder=str(MODEL_CACHE_FOLDER),
        local_files_only=not allow_download,
        device="cpu",
        max_length=MAX_LENGTH,
        activation_fn=torch.nn.Identity(),
    )
    actual_revision = getattr(model.model.config, "_commit_hash", None)
    if actual_revision != RERANKER_MODEL_REVISION:
        raise RuntimeError(
            f"Reranker revision mismatch: {actual_revision!r} != {RERANKER_MODEL_REVISION!r}"
        )
    if model.max_seq_length != MAX_LENGTH:
        raise RuntimeError(f"Reranker max_length mismatch: {model.max_seq_length}")
    return model


def snapshot_metadata() -> tuple[int, str, str]:
    repository_folder = "models--" + RERANKER_MODEL_REPOSITORY.replace("/", "--")
    snapshot = MODEL_CACHE_FOLDER / repository_folder / "snapshots" / RERANKER_MODEL_REVISION
    if not snapshot.is_dir():
        raise FileNotFoundError(f"Pinned reranker snapshot not found: {snapshot}")
    files = sorted(path for path in snapshot.rglob("*") if path.is_file())
    records = [
        {
            "path": path.relative_to(snapshot).as_posix(),
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in files
    ]
    weight_files = [record for record in records if record["path"] == "model.safetensors"]
    if len(weight_files) != 1:
        raise ValueError("Pinned reranker snapshot must contain model.safetensors")
    weights_hash = weight_files[0]["sha256"]
    if weights_hash != RERANKER_MODEL_WEIGHTS_SHA256:
        raise ValueError("Reranker model.safetensors hash differs from locked contract")
    return len(records), sha256_bytes(canonical_json_bytes(records)), weights_hash


def dense_rankings(
    questions: list[dict], chunks: list[dict], vectors: np.ndarray
) -> tuple[np.ndarray, list[list[int]], int, int]:
    model = load_dense_query_model()
    query_vectors = model.encode(
        [question["question"] for question in questions],
        batch_size=32,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    query_vectors = np.asarray(query_vectors, dtype=np.float32, order="C")
    score_matrix = query_vectors @ vectors.T
    rankings = [
        sorted(
            range(len(chunks)),
            key=lambda index: (-float(scores[index]), chunks[index]["chunk_id"]),
        )
        for scores in score_matrix
    ]

    baseline_rows = {
        row["question_id"]: row
        for row in load_csv(DENSE_BASELINE_RESULTS_FILE)
        if row["retrieval_method"] == SELECTED_RETRIEVAL_METHOD
    }
    if len(baseline_rows) != 35:
        raise ValueError("Expected 35 locked Dense baseline detail rows")
    id_matches = 0
    score_matches = 0
    for question_index, question in enumerate(questions):
        top_indices = rankings[question_index][:10]
        top_ids = [chunks[index]["chunk_id"] for index in top_indices]
        top_scores = [round(float(score_matrix[question_index, index]), 8) for index in top_indices]
        baseline = baseline_rows[question["question_id"]]
        id_matches += int(top_ids == json.loads(baseline["top_10_chunk_ids_json"]))
        score_matches += int(top_scores == json.loads(baseline["top_10_scores_json"]))
    if id_matches != 35 or score_matches != 35:
        raise RuntimeError(f"Dense baseline mismatch: ids={id_matches}/35 scores={score_matches}/35")
    return score_matrix, rankings, id_matches, score_matches


def pair_token_profile(model: CrossEncoder, pairs: list[tuple[str, str]]) -> tuple[int, int]:
    encoded = model.tokenizer(
        [pair[0] for pair in pairs],
        [pair[1] for pair in pairs],
        add_special_tokens=True,
        padding=False,
        truncation=False,
        return_length=True,
    )
    lengths = [int(value) for value in encoded["length"]]
    return max(lengths), sum(length > MAX_LENGTH for length in lengths)


def main() -> None:
    args = parse_args()
    output_folder = args.output_folder.resolve() if args.output_folder else REPORT_FOLDER
    output_results_file = output_folder / RESULTS_FILE.name
    output_comparison_file = output_folder / COMPARISON_FILE.name
    output_question_comparison_file = output_folder / QUESTION_COMPARISON_FILE.name
    output_validation_file = output_folder / VALIDATION_FILE.name
    output_manifest_file = output_folder / MANIFEST_FILE.name
    torch.manual_seed(0)
    np.random.seed(0)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)

    dense_manifest, chunks, vectors, questions, out_of_scope, ground_truth = (
        validate_static_inputs()
    )
    dense_scores, dense_rankings_by_question, dense_id_matches, dense_score_matches = (
        dense_rankings(questions, chunks, vectors)
    )

    candidate_first_relevant_count = 0
    candidate_full_evidence_count = 0
    pairs = []
    for question_index, question in enumerate(questions):
        candidates = dense_rankings_by_question[question_index][:CANDIDATE_DEPTH]
        ranges = ground_truth[question["question_id"]]
        covered = set()
        first_relevant = False
        for chunk_index in candidates:
            hit_ranges = covered_range_indices(chunks[chunk_index], ranges)
            first_relevant = first_relevant or bool(hit_ranges)
            covered.update(hit_ranges)
            pairs.append((question["question"], chunks[chunk_index]["chunk_text"]))
        candidate_first_relevant_count += int(first_relevant)
        candidate_full_evidence_count += int(
            covered == {item["range_index"] for item in ranges}
        )
    if candidate_first_relevant_count != 35 or candidate_full_evidence_count != 35:
        raise RuntimeError("Dense Top 50 does not contain complete Ground Truth coverage")
    if len(pairs) != 35 * CANDIDATE_DEPTH:
        raise RuntimeError("Unexpected reranker pair count")

    reranker = load_reranker(args.allow_model_download)
    snapshot_file_count, snapshot_hash, weights_hash = snapshot_metadata()
    pair_token_length_max, truncated_pair_count = pair_token_profile(reranker, pairs)
    raw_scores = reranker.predict(
        pairs,
        batch_size=BATCH_SIZE,
        show_progress_bar=False,
        activation_fn=torch.nn.Identity(),
        apply_softmax=False,
        convert_to_numpy=True,
    )
    reranker_scores = np.asarray(raw_scores, dtype=np.float32).reshape(-1)
    if reranker_scores.shape != (len(pairs),) or not np.isfinite(reranker_scores).all():
        raise RuntimeError("Reranker scores must be one finite float32 value per pair")

    identity = {
        "reranking_version": RERANKING_VERSION,
        "canonical_gold_sha256": sha256_file(CANONICAL_GOLD_FILE),
        "evaluation_sha256": sha256_file(EVALUATION_FILE),
        "dense_index_content_sha256": dense_manifest["index_content_sha256"],
        "retrieval_decision_sha256": sha256_file(RETRIEVAL_DECISION_FILE),
        "reranker_model_repository": RERANKER_MODEL_REPOSITORY,
        "reranker_model_revision": RERANKER_MODEL_REVISION,
        "reranker_snapshot_content_sha256": snapshot_hash,
        "candidate_depth": CANDIDATE_DEPTH,
        "output_top_k": OUTPUT_TOP_K,
        "max_length": MAX_LENGTH,
        "batch_size": BATCH_SIZE,
    }
    run_id = f"mit60001_rerank_{sha256_bytes(canonical_json_bytes(identity))[:16]}"

    detail_rows = []
    question_rows = []
    metrics_by_method = {SELECTED_RETRIEVAL_METHOD: [], RERANKED_METHOD: []}
    offset = 0
    for question_index, question in enumerate(questions):
        dense_ranking = dense_rankings_by_question[question_index]
        candidates = dense_ranking[:CANDIDATE_DEPTH]
        candidate_scores = reranker_scores[offset : offset + CANDIDATE_DEPTH]
        offset += CANDIDATE_DEPTH
        reranked = sorted(
            candidates,
            key=lambda chunk_index: (
                -float(candidate_scores[candidates.index(chunk_index)]),
                candidates.index(chunk_index),
                chunks[chunk_index]["chunk_id"],
            ),
        )
        reranker_score_by_chunk = {
            chunk_index: float(candidate_scores[dense_rank])
            for dense_rank, chunk_index in enumerate(candidates)
        }
        ranges = ground_truth[question["question_id"]]
        dense_metrics = question_metrics(dense_ranking, chunks, ranges)
        reranked_metrics = question_metrics(reranked, chunks, ranges)
        metrics_by_method[SELECTED_RETRIEVAL_METHOD].append(dense_metrics)
        metrics_by_method[RERANKED_METHOD].append(reranked_metrics)

        method_rankings = {
            SELECTED_RETRIEVAL_METHOD: dense_ranking,
            RERANKED_METHOD: reranked,
        }
        for method, ranking in method_rankings.items():
            metrics = dense_metrics if method == SELECTED_RETRIEVAL_METHOD else reranked_metrics
            top_indices = ranking[:10]
            top_ids = [chunks[index]["chunk_id"] for index in top_indices]
            if method == SELECTED_RETRIEVAL_METHOD:
                top_scores = [
                    round(float(dense_scores[question_index, index]), 8) for index in top_indices
                ]
                score_type = "dense_cosine"
            else:
                top_scores = [round(reranker_score_by_chunk[index], 8) for index in top_indices]
                score_type = "cross_encoder_raw_logit"
            top_flags = [bool(covered_range_indices(chunks[index], ranges)) for index in top_indices]
            detail_rows.append({
                "reranking_run_id": run_id,
                "retrieval_method": method,
                "question_id": question["question_id"],
                "candidate_depth": CANDIDATE_DEPTH,
                "first_relevant_rank": metrics["first_relevant_rank"],
                "reciprocal_rank": round(metrics["reciprocal_rank"], 9),
                "chunks_to_full_coverage": metrics["chunks_to_full_coverage"],
                "score_type": score_type,
                "top_3_chunk_ids_json": json.dumps(top_ids[:3], ensure_ascii=False, separators=(",", ":")),
                "top_3_scores_json": json.dumps(top_scores[:3], separators=(",", ":")),
                "top_3_relevant_flags_json": json.dumps(top_flags[:3], separators=(",", ":")),
                "top_10_chunk_ids_json": json.dumps(top_ids, ensure_ascii=False, separators=(",", ":")),
                "top_10_scores_json": json.dumps(top_scores, separators=(",", ":")),
                "top_10_relevant_flags_json": json.dumps(top_flags, separators=(",", ":")),
            })

        dense_top3 = dense_ranking[:3]
        reranked_top3 = reranked[:3]
        first_rank_delta = (
            reranked_metrics["first_relevant_rank"] - dense_metrics["first_relevant_rank"]
        )
        full_rank_delta = (
            reranked_metrics["chunks_to_full_coverage"]
            - dense_metrics["chunks_to_full_coverage"]
        )
        question_rows.append({
            "reranking_run_id": run_id,
            "question_id": question["question_id"],
            "question": question["question"],
            "category": question["category"],
            "dense_first_relevant_rank": dense_metrics["first_relevant_rank"],
            "reranked_first_relevant_rank": reranked_metrics["first_relevant_rank"],
            "reranked_first_rank_delta_vs_dense": first_rank_delta,
            "first_rank_outcome": "improved" if first_rank_delta < 0 else "worse" if first_rank_delta > 0 else "equal",
            "dense_chunks_to_full_coverage": dense_metrics["chunks_to_full_coverage"],
            "reranked_chunks_to_full_coverage": reranked_metrics["chunks_to_full_coverage"],
            "reranked_full_coverage_rank_delta_vs_dense": full_rank_delta,
            "full_coverage_outcome": "improved" if full_rank_delta < 0 else "worse" if full_rank_delta > 0 else "equal",
            "dense_top_3_relevant_count": sum(bool(covered_range_indices(chunks[index], ranges)) for index in dense_top3),
            "reranked_top_3_relevant_count": sum(bool(covered_range_indices(chunks[index], ranges)) for index in reranked_top3),
            "top_3_overlap_count": len(set(dense_top3) & set(reranked_top3)),
            "dense_top_3_chunk_ids_json": json.dumps([chunks[index]["chunk_id"] for index in dense_top3], ensure_ascii=False, separators=(",", ":")),
            "reranked_top_3_chunk_ids_json": json.dumps([chunks[index]["chunk_id"] for index in reranked_top3], ensure_ascii=False, separators=(",", ":")),
            "review_status": "pending_human_decision",
        })

    comparisons = [
        aggregate_metrics(
            method,
            run_id,
            metrics_by_method[method],
            sum(map(len, ground_truth.values())),
        )
        for method in (SELECTED_RETRIEVAL_METHOD, RERANKED_METHOD)
    ]
    locked_baseline_rows = [
        row
        for row in load_csv(DENSE_BASELINE_COMPARISON_FILE)
        if row["retrieval_method"] == SELECTED_RETRIEVAL_METHOD
    ]
    if len(locked_baseline_rows) != 1:
        raise ValueError("Expected one locked Dense comparison row")
    dense_comparison = comparisons[0]
    dense_baseline_metrics_match = all(
        abs(float(dense_comparison[field]) - float(locked_baseline_rows[0][field])) <= 1e-9
        for field in METRIC_FIELDS
    )
    if not dense_baseline_metrics_match:
        raise RuntimeError("Recomputed Dense metrics differ from selected baseline")

    validation_rows = [
        {"check_name": "canonical_gold_hash", "status": "passed", "actual": identity["canonical_gold_sha256"], "expected": dense_manifest["canonical_gold_sha256"]},
        {"check_name": "evaluation_hash", "status": "passed", "actual": identity["evaluation_sha256"], "expected": "81d5a1374118b01d850d7c4808edf89b9432036a4488c49f5150720aa3fc8dee"},
        {"check_name": "selected_retrieval_method", "status": "passed", "actual": SELECTED_RETRIEVAL_METHOD, "expected": SELECTED_RETRIEVAL_METHOD},
        {"check_name": "question_count", "status": "passed", "actual": len(questions), "expected": 35},
        {"check_name": "ground_truth_range_count", "status": "passed", "actual": sum(map(len, ground_truth.values())), "expected": 57},
        {"check_name": "candidate_pair_count", "status": "passed", "actual": len(pairs), "expected": 1750},
        {"check_name": "candidate_first_relevant_count", "status": "passed", "actual": candidate_first_relevant_count, "expected": 35},
        {"check_name": "candidate_full_evidence_count", "status": "passed", "actual": candidate_full_evidence_count, "expected": 35},
        {"check_name": "dense_top_10_id_match_count", "status": "passed", "actual": dense_id_matches, "expected": 35},
        {"check_name": "dense_top_10_score_match_count", "status": "passed", "actual": dense_score_matches, "expected": 35},
        {"check_name": "dense_baseline_metrics_match", "status": "passed", "actual": dense_baseline_metrics_match, "expected": True},
        {"check_name": "reranker_model_revision", "status": "passed", "actual": RERANKER_MODEL_REVISION, "expected": RERANKER_MODEL_REVISION},
        {"check_name": "reranker_weights_hash", "status": "passed", "actual": weights_hash, "expected": RERANKER_MODEL_WEIGHTS_SHA256},
        {"check_name": "finite_reranker_scores", "status": "passed", "actual": int(np.isfinite(reranker_scores).sum()), "expected": len(pairs)},
    ]

    results_bytes = serialize_csv(detail_rows)
    comparison_bytes = serialize_csv(comparisons)
    question_bytes = serialize_csv(question_rows)
    validation_bytes = serialize_csv(validation_rows)
    manifest = {
        "$schema": "../../schemas/cross_encoder_reranking_manifest_v1.schema.json",
        "schema_version": "cross_encoder_reranking_manifest_v1",
        "reranking_run_id": run_id,
        "reranking_version": RERANKING_VERSION,
        "scope_version": "mit_60001_fall_2016_v1",
        "canonical_gold_file": project_relative(CANONICAL_GOLD_FILE),
        "canonical_gold_sha256": identity["canonical_gold_sha256"],
        "evaluation_file": project_relative(EVALUATION_FILE),
        "evaluation_sha256": identity["evaluation_sha256"],
        "dense_index_manifest_file": project_relative(DENSE_MANIFEST_FILE),
        "dense_index_manifest_sha256": sha256_file(DENSE_MANIFEST_FILE),
        "dense_index_content_sha256": dense_manifest["index_content_sha256"],
        "retrieval_decision_file": project_relative(RETRIEVAL_DECISION_FILE),
        "retrieval_decision_sha256": identity["retrieval_decision_sha256"],
        "selected_retrieval_method": SELECTED_RETRIEVAL_METHOD,
        "dense_model_repository": DENSE_MODEL_REPOSITORY,
        "dense_model_revision": DENSE_MODEL_REVISION,
        "reranker_model_repository": RERANKER_MODEL_REPOSITORY,
        "reranker_model_revision": RERANKER_MODEL_REVISION,
        "reranker_actual_revision": getattr(reranker.model.config, "_commit_hash", None),
        "reranker_model_weights_sha256": weights_hash,
        "reranker_snapshot_file_count": snapshot_file_count,
        "reranker_snapshot_content_sha256": snapshot_hash,
        "model_cache_policy": "project_local_gitignored_data_models",
        "device": "cpu",
        "candidate_depth": CANDIDATE_DEPTH,
        "output_top_k": OUTPUT_TOP_K,
        "max_length": MAX_LENGTH,
        "batch_size": BATCH_SIZE,
        "score_function": "raw_identity_logit_float32",
        "ranking_tie_break": "score_desc_then_dense_rank_asc_then_chunk_id_asc",
        "question_count": len(questions),
        "excluded_out_of_scope_question_count": len(out_of_scope),
        "ground_truth_range_count": sum(map(len, ground_truth.values())),
        "corpus_chunk_count": len(chunks),
        "candidate_pair_count": len(pairs),
        "candidate_first_relevant_count": candidate_first_relevant_count,
        "candidate_full_evidence_count": candidate_full_evidence_count,
        "pair_token_length_max": pair_token_length_max,
        "truncated_pair_count": truncated_pair_count,
        "relevance_rule": "same_video_and_source_segment_interval_intersection",
        "dense_baseline_metrics_match": dense_baseline_metrics_match,
        "dense_top_10_id_match_count": dense_id_matches,
        "dense_top_10_score_match_count": dense_score_matches,
        "results_file": project_relative(RESULTS_FILE),
        "results_sha256": sha256_bytes(results_bytes),
        "comparison_file": project_relative(COMPARISON_FILE),
        "comparison_sha256": sha256_bytes(comparison_bytes),
        "question_comparison_file": project_relative(QUESTION_COMPARISON_FILE),
        "question_comparison_sha256": sha256_bytes(question_bytes),
        "validation_file": project_relative(VALIDATION_FILE),
        "validation_sha256": sha256_bytes(validation_bytes),
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
        "sentence_transformers_version": sentence_transformers.__version__,
        "selection_status": "pending_human_decision",
        "validation_status": "passed",
    }
    schema = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(manifest)

    write_atomic(output_results_file, results_bytes)
    write_atomic(output_comparison_file, comparison_bytes)
    write_atomic(output_question_comparison_file, question_bytes)
    write_atomic(output_validation_file, validation_bytes)
    write_atomic(
        output_manifest_file,
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n",
    )
    print(json.dumps({
        "reranking_run_id": run_id,
        "candidate_depth": CANDIDATE_DEPTH,
        "candidate_pair_count": len(pairs),
        "pair_token_length_max": pair_token_length_max,
        "truncated_pair_count": truncated_pair_count,
        "comparison": comparisons,
        "validation_status": "passed",
        "selection_status": "pending_human_decision",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
