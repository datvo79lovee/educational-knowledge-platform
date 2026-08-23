"""Run Phase 9 M2 retrieval only; do not calculate relevance or quality metrics."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
from pathlib import Path

import numpy as np
import sentence_transformers
from sentence_transformers import SentenceTransformer
import torch
import transformers


PROJECT_ROOT = Path(__file__).resolve().parents[2]
M1_ARTIFACT = PROJECT_ROOT / "evaluation/mit_60001/multilingual/paired_intents_v1.jsonl"
M1_MANIFEST = PROJECT_ROOT / "evaluation/mit_60001/multilingual/m1_manifest.json"
GOLD_FILE = PROJECT_ROOT / "data/gold/mit_60001/chunks.jsonl"
INDEX_MANIFEST_FILE = PROJECT_ROOT / "reports/09_embedding/embedding_index_manifest.json"
CANONICAL_RETRIEVAL_MANIFEST = PROJECT_ROOT / "reports/09_embedding/production_index_retrieval_manifest.json"
CANONICAL_RETRIEVAL_RESULTS = PROJECT_ROOT / "reports/09_embedding/production_index_retrieval_results.csv"
RESULT_SCHEMA = PROJECT_ROOT / "schemas/multilingual_retrieval_result_v1.schema.json"
MANIFEST_SCHEMA = PROJECT_ROOT / "schemas/multilingual_retrieval_manifest_v1.schema.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports/27_multilingual_dense_retrieval"
RESULTS_NAME = "multilingual_dense_retrieval_results.jsonl"
MANIFEST_NAME = "multilingual_dense_retrieval_manifest.json"
RETRIEVAL_METHOD = "dense_baseline_v1"
QUERY_VARIANTS = ("en_canonical", "vi_literal_en")
CANONICAL_SCORE_TOLERANCE = 1e-6


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def canonical_json_bytes(value: dict) -> bytes:
    return canonical_json(value).encode("utf-8")


def jsonl_bytes(rows: list[dict]) -> bytes:
    return ("\n".join(canonical_json(row) for row in rows) + "\n").encode("utf-8")


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_bytes(content)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def validated_inputs() -> tuple[list[dict], dict, list[dict], list[dict], np.ndarray, dict]:
    m1_manifest = json.loads(M1_MANIFEST.read_text(encoding="utf-8"))
    if m1_manifest["status"] != "frozen" or m1_manifest["m1_gate_status"] != "passed":
        raise ValueError("M1 must be frozen and passed before M2")
    if m1_manifest["artifacts"]["paired_artifact"]["sha256"] != sha256_file(M1_ARTIFACT):
        raise ValueError("Frozen M1 paired artifact hash mismatch")
    paired_rows = load_jsonl(M1_ARTIFACT)
    if len(paired_rows) != 20 or len({row["intent_id"] for row in paired_rows}) != 20:
        raise ValueError("M1 paired artifact must contain 20 unique intents")

    index_manifest = json.loads(INDEX_MANIFEST_FILE.read_text(encoding="utf-8"))
    if index_manifest["validation_status"] != "passed" or index_manifest["chunk_count"] != 861:
        raise ValueError("Canonical Dense index manifest is not valid")
    file_contracts = {
        GOLD_FILE: index_manifest["canonical_gold_sha256"],
        PROJECT_ROOT / index_manifest["embeddings_file"]: index_manifest["embeddings_sha256"],
        PROJECT_ROOT / index_manifest["metadata_file"]: index_manifest["metadata_sha256"],
    }
    for path, expected_hash in file_contracts.items():
        if sha256_file(path) != expected_hash:
            raise ValueError(f"Canonical index input hash mismatch: {path.name}")

    gold_rows = load_jsonl(GOLD_FILE)
    metadata_rows = load_jsonl(PROJECT_ROOT / index_manifest["metadata_file"])
    vectors = np.load(PROJECT_ROOT / index_manifest["embeddings_file"], allow_pickle=False)
    if vectors.shape != (861, 384) or vectors.dtype != np.float32:
        raise ValueError("Canonical embedding matrix shape/dtype changed")
    if len(gold_rows) != 861 or len(metadata_rows) != 861:
        raise ValueError("Canonical Gold/metadata count changed")
    for position, (chunk, metadata) in enumerate(zip(gold_rows, metadata_rows, strict=True)):
        if metadata["index_position"] != position or metadata["chunk_id"] != chunk["chunk_id"]:
            raise ValueError(f"Canonical metadata order mismatch at position {position}")

    canonical_manifest = json.loads(CANONICAL_RETRIEVAL_MANIFEST.read_text(encoding="utf-8"))
    if canonical_manifest["index_content_sha256"] != index_manifest["index_content_sha256"]:
        raise ValueError("Canonical retrieval/index identity mismatch")
    return paired_rows, m1_manifest, gold_rows, metadata_rows, vectors, index_manifest


def build_outputs(output_dir: Path) -> tuple[Path, Path]:
    paired_rows, m1_manifest, gold_rows, metadata_rows, vectors, index_manifest = validated_inputs()
    model_repository = index_manifest["model_repository"]
    model_revision = index_manifest["model_revision"]
    query_specs = []
    for row in paired_rows:
        query_specs.extend(
            [
                (row["intent_id"], "en_canonical", row["question_en"]),
                (row["intent_id"], "vi_literal_en", row["literal_en"]),
            ]
        )
    if len(query_specs) != 40 or any(text != text.strip() for _, _, text in query_specs):
        raise ValueError("M2 query package must contain exactly 40 non-normalized frozen query strings")

    model = SentenceTransformer(
        model_repository,
        revision=model_revision,
        local_files_only=True,
        device="cpu",
    )
    actual_revision = getattr(model._first_module().auto_model.config, "_commit_hash", None)
    if actual_revision != model_revision or model.get_embedding_dimension() != 384:
        raise RuntimeError("M2 query encoder differs from canonical index encoder")
    if model.max_seq_length != index_manifest["model_max_sequence_length"]:
        raise RuntimeError("M2 query encoder max sequence length changed")
    query_vectors = model.encode(
        [item[2] for item in query_specs],
        batch_size=32,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    query_vectors = np.asarray(query_vectors, dtype=np.float32, order="C")
    if query_vectors.shape != (40, 384) or not np.isfinite(query_vectors).all():
        raise RuntimeError("M2 query encoder returned invalid vectors")
    scores_matrix = query_vectors @ vectors.T

    identity = {
        "artifact_version": "mit_60001_multilingual_m2_v1",
        "m1_paired_artifact_sha256": sha256_file(M1_ARTIFACT),
        "m1_manifest_sha256": sha256_file(M1_MANIFEST),
        "index_content_sha256": index_manifest["index_content_sha256"],
        "model_revision": model_revision,
        "retrieval_method": RETRIEVAL_METHOD,
        "retrieval_depth": len(gold_rows),
        "query_variants": list(QUERY_VARIANTS),
    }
    retrieval_run_id = "mit60001_multilingual_dense_" + sha256_bytes(canonical_json_bytes(identity))[:16]
    result_rows = []
    for query_index, (intent_id, query_variant, query_text) in enumerate(query_specs):
        scores = scores_matrix[query_index]
        ranked_indices = sorted(
            range(len(gold_rows)),
            key=lambda index: (-float(scores[index]), gold_rows[index]["chunk_id"]),
        )
        result_rows.append(
            {
                "schema_version": "multilingual_retrieval_result_v1",
                "retrieval_run_id": retrieval_run_id,
                "intent_id": intent_id,
                "query_variant": query_variant,
                "query_text": query_text,
                "retrieval_depth": len(ranked_indices),
                "results": [
                    {
                        "rank": rank,
                        "chunk_id": gold_rows[index]["chunk_id"],
                        "score": round(float(scores[index]), 8),
                    }
                    for rank, index in enumerate(ranked_indices, start=1)
                ],
            }
        )

    by_key = {(row["intent_id"], row["query_variant"]): row for row in result_rows}
    identical_query_ids = [
        row["intent_id"] for row in paired_rows if row["question_en"] == row["literal_en"]
    ]
    identical_equivalent_count = sum(
        by_key[(intent_id, "en_canonical")]["results"]
        == by_key[(intent_id, "vi_literal_en")]["results"]
        for intent_id in identical_query_ids
    )
    if identical_equivalent_count != len(identical_query_ids):
        raise RuntimeError("Identical frozen query strings produced different retrieval outputs")

    baseline_by_id = {row["question_id"]: row for row in load_csv(CANONICAL_RETRIEVAL_RESULTS)}
    en_id_matches = 0
    en_score_matches = 0
    max_score_delta = 0.0
    for paired in paired_rows:
        current = by_key[(paired["intent_id"], "en_canonical")]["results"][:10]
        baseline = baseline_by_id[paired["intent_id"]]
        baseline_ids = json.loads(baseline["top_10_chunk_ids_json"])
        baseline_scores = json.loads(baseline["top_10_scores_json"])
        en_id_matches += int([item["chunk_id"] for item in current] == baseline_ids)
        deltas = [abs(item["score"] - expected) for item, expected in zip(current, baseline_scores, strict=True)]
        row_max_delta = max(deltas)
        max_score_delta = max(max_score_delta, row_max_delta)
        en_score_matches += int(row_max_delta <= CANONICAL_SCORE_TOLERANCE)
    if en_id_matches != 20 or en_score_matches != 20:
        raise RuntimeError("M2 English branch differs from canonical Dense baseline")

    results_content = jsonl_bytes(result_rows)
    results_path = output_dir / RESULTS_NAME
    manifest_path = output_dir / MANIFEST_NAME
    write_atomic(results_path, results_content)
    manifest = {
        "$schema": "../../schemas/multilingual_retrieval_manifest_v1.schema.json",
        "schema_version": "multilingual_retrieval_manifest_v1",
        "artifact_version": "mit_60001_multilingual_m2_v1",
        "status": "retrieval_complete",
        "retrieval_run_id": retrieval_run_id,
        "m1": {
            "paired_artifact_path": "evaluation/mit_60001/multilingual/paired_intents_v1.jsonl",
            "paired_artifact_sha256": sha256_file(M1_ARTIFACT),
            "manifest_path": "evaluation/mit_60001/multilingual/m1_manifest.json",
            "manifest_sha256": sha256_file(M1_MANIFEST),
            "m1_artifact_version": m1_manifest["artifact_version"],
            "m1_status": m1_manifest["status"],
        },
        "index": {
            "canonical_gold_sha256": index_manifest["canonical_gold_sha256"],
            "index_manifest_path": "reports/09_embedding/embedding_index_manifest.json",
            "index_manifest_sha256": sha256_file(INDEX_MANIFEST_FILE),
            "index_run_id": index_manifest["index_run_id"],
            "index_content_sha256": index_manifest["index_content_sha256"],
            "embeddings_sha256": index_manifest["embeddings_sha256"],
            "metadata_sha256": index_manifest["metadata_sha256"],
            "chunk_id_order_sha256": index_manifest["chunk_id_order_sha256"],
            "chunk_count": len(gold_rows),
            "embedding_shape": index_manifest["embedding_shape"],
            "embedding_dtype": index_manifest["embedding_dtype"],
            "index_backend": index_manifest["index_backend"],
            "model_repository": model_repository,
            "model_revision": model_revision,
        },
        "retrieval": {
            "retrieval_method": RETRIEVAL_METHOD,
            "similarity": index_manifest["similarity"],
            "query_normalize_embeddings": True,
            "ranking_tie_break": "score_desc_then_chunk_id_asc",
            "retrieval_depth": len(gold_rows),
            "exported_depth": len(gold_rows),
            "canonical_metric_ranking_semantics": "full_corpus_ranking; M3 may derive first relevant rank without Top-K truncation",
            "canonical_k_values": [1, 3, 5, 10],
            "score_round_decimal_places": 8,
        },
        "execution": {
            "number_of_intents": len(paired_rows),
            "number_of_query_variants": len(result_rows),
            "query_variant_counts": {"en_canonical": 20, "vi_literal_en": 20},
            "query_source_fields": {"en_canonical": "question_en", "vi_literal_en": "literal_en"},
            "query_encoder_input_count": len(query_specs),
            "translator_calls": 0,
            "llm_calls": 0,
            "generator_calls": 0,
            "ground_truth_fields_used_for_retrieval": [],
            "quality_metrics_computed": False,
        },
        "validation": {
            "retrieval_record_count": len(result_rows),
            "missing_intent_count": 0,
            "duplicate_branch_count": 0,
            "invalid_chunk_id_count": 0,
            "identical_query_pair_count": len(identical_query_ids),
            "identical_query_result_equivalent_count": identical_equivalent_count,
            "canonical_en_top_10_id_match_count": en_id_matches,
            "canonical_en_top_10_score_match_count": en_score_matches,
            "canonical_en_score_tolerance": CANONICAL_SCORE_TOLERANCE,
            "canonical_en_max_score_delta": round(max_score_delta, 12),
        },
        "artifacts": {
            "results": {
                "path": "reports/27_multilingual_dense_retrieval/multilingual_dense_retrieval_results.jsonl",
                "sha256": sha256_bytes(results_content),
                "record_count": len(result_rows),
            },
            "result_schema": {
                "path": "schemas/multilingual_retrieval_result_v1.schema.json",
                "sha256": sha256_file(RESULT_SCHEMA),
            },
            "canonical_retrieval_manifest": {
                "path": "reports/09_embedding/production_index_retrieval_manifest.json",
                "sha256": sha256_file(CANONICAL_RETRIEVAL_MANIFEST),
            },
            "canonical_retrieval_results": {
                "path": "reports/09_embedding/production_index_retrieval_results.csv",
                "sha256": sha256_file(CANONICAL_RETRIEVAL_RESULTS),
            },
        },
        "software": {
            "python_version": platform.python_version(),
            "numpy_version": np.__version__,
            "torch_version": torch.__version__,
            "transformers_version": transformers.__version__,
            "sentence_transformers_version": sentence_transformers.__version__,
        },
        "validation_status": "passed",
    }
    manifest_content = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    write_atomic(manifest_path, manifest_content)
    print(
        json.dumps(
            {
                "validation_status": "passed",
                "retrieval_run_id": retrieval_run_id,
                "retrieval_record_count": len(result_rows),
                "retrieval_depth": len(gold_rows),
                "translator_calls": 0,
                "quality_metrics_computed": False,
                "identical_query_pairs": len(identical_query_ids),
                "canonical_en_top_10_id_matches": en_id_matches,
            },
            ensure_ascii=False,
        )
    )
    return results_path, manifest_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    torch.manual_seed(0)
    np.random.seed(0)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    build_outputs(args.output_dir.resolve())


if __name__ == "__main__":
    main()
