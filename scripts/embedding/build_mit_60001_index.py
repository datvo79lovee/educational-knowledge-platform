"""Build exact dense index directly from canonical MIT 6.0001 Gold chunks.

The public build path validates Gold against the canonical chunking config and
Gold schema before encoding.  It never reads historical selection reports.
"""

import argparse
import hashlib
import io
import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer
import torch
from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CANONICAL_GOLD_FILE = Path("data/gold/mit_60001/chunks.jsonl")
CANONICAL_CHUNKING_CONFIG_FILE = Path("config/mit_60001_canonical_chunking.json")
GOLD_SCHEMA_FILE = Path("schemas/gold_chunk_v1.schema.json")
INDEX_DIR = Path("data/indexes/mit_60001")
EMBEDDINGS_FILE = INDEX_DIR / "embeddings.npy"
METADATA_FILE = INDEX_DIR / "metadata.jsonl"
RUNTIME_MANIFEST_FILE = INDEX_DIR / "manifest.json"
RUNTIME_MANIFEST_SCHEMA_FILE = Path("schemas/runtime_index_manifest_v1.schema.json")

MODEL_REPOSITORY = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
EXPECTED_DIMENSION = 384
EXPECTED_CHUNK_COUNT = 861
EXPECTED_VIDEO_COUNT = 38
EXPECTED_SCOPE_VERSION = "mit_60001_fall_2016_v1"
BATCH_SIZE = 32
NORM_TOLERANCE = 1e-5
INDEX_VERSION = "mit60001_exact_dense_v1"


def sha256_bytes(content: bytes) -> str:
    """Tính SHA-256 trên bytes chính xác của artifact."""

    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    """Tính SHA-256 của file mà không thay đổi nội dung."""

    return sha256_bytes(path.read_bytes())


def canonical_json_bytes(value: object) -> bytes:
    """Serialize identity payload ổn định để tạo run ID."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def write_atomic(path: Path, content: bytes) -> None:
    """Ghi artifact qua file tạm rồi replace đích."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_bytes(content)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def load_jsonl(path: Path) -> list[dict]:
    """Đọc JSONL, bỏ qua dòng trắng."""

    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def serialize_jsonl(records: list[dict]) -> bytes:
    """Serialize metadata theo thứ tự index position, một record mỗi dòng."""

    lines = [
        json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for record in records
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def serialize_npy(vectors: np.ndarray) -> bytes:
    """Serialize ma trận NumPy không pickle để index có thể hash và load an toàn."""

    buffer = io.BytesIO()
    np.save(buffer, vectors, allow_pickle=False)
    return buffer.getvalue()


def serialize_runtime_manifest(manifest: dict) -> bytes:
    """Serialize manifest runtime theo layout byte-stable đã được canonicalize.

    Runtime manifest hiện chỉ có scalar JSON và ``embedding_shape``. Render từng
    field top-level giữ array shape trên một dòng, nên rebuild không đổi SHA chỉ vì
    JSON pretty-printer tự xuống dòng mảng ngắn.
    """

    keys = sorted(manifest)
    lines = ["{"]
    for index, key in enumerate(keys):
        encoded_key = json.dumps(key, ensure_ascii=False)
        encoded_value = json.dumps(manifest[key], ensure_ascii=False, sort_keys=True)
        suffix = "," if index < len(keys) - 1 else ""
        lines.append(f"  {encoded_key}: {encoded_value}{suffix}")
    lines.append("}")
    return ("\n".join(lines) + "\n").encode("utf-8")


def load_canonical_chunking_config() -> dict:
    """Load the frozen current chunking configuration, not its historical selection record."""

    config = json.loads(CANONICAL_CHUNKING_CONFIG_FILE.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "scope_version",
        "chunking_version",
        "chunking_config_id",
        "strategy",
        "minimum_wordpieces",
        "preferred_wordpieces",
        "maximum_wordpieces",
        "overlap_target_wordpieces",
        "encoder",
    }
    if set(config) != required or config["schema_version"] != "canonical_chunking_config_v1":
        raise ValueError("Canonical chunking config has an invalid shape")
    if config["scope_version"] != EXPECTED_SCOPE_VERSION:
        raise ValueError("Canonical chunking config has an unexpected scope")
    if config["chunking_version"] != "mit_60001_chunk_v1":
        raise ValueError("Canonical chunking config has an unexpected version")
    if config["strategy"] != "semantic_cosine":
        raise ValueError("Canonical chunking config has an unsupported strategy")
    if config["encoder"] != {"repository": MODEL_REPOSITORY, "revision": MODEL_REVISION}:
        raise ValueError("Canonical chunking config differs from the pinned index encoder")
    return config


def validated_canonical_input() -> tuple[list[dict], dict, str]:
    """Validate the canonical Gold file directly against current config and schema."""

    config = load_canonical_chunking_config()
    canonical_hash = sha256_file(CANONICAL_GOLD_FILE)
    records = load_jsonl(CANONICAL_GOLD_FILE)
    schema = json.loads(GOLD_SCHEMA_FILE.read_text(encoding="utf-8"))
    schema_errors = [
        error.message
        for record in records
        for error in Draft202012Validator(schema).iter_errors(record)
    ]
    if schema_errors:
        raise ValueError(f"Canonical Gold schema validation failed: {schema_errors[0]}")
    chunk_ids = [record["chunk_id"] for record in records]
    if len(records) != EXPECTED_CHUNK_COUNT or len(set(chunk_ids)) != EXPECTED_CHUNK_COUNT:
        raise ValueError("Canonical Gold must contain 861 unique chunk IDs")
    if len({record["video_id"] for record in records}) != EXPECTED_VIDEO_COUNT:
        raise ValueError("Canonical Gold must contain 38 videos")
    if {record["scope_version"] for record in records} != {config["scope_version"]}:
        raise ValueError("Canonical Gold contains a record outside the target scope")
    if {record["chunking_config_id"] for record in records} != {config["chunking_config_id"]}:
        raise ValueError("Canonical Gold contains a non-selected chunk configuration")
    if any(not record["chunk_text"].strip() for record in records):
        raise ValueError("Canonical Gold contains empty chunk text")
    return records, config, canonical_hash


def load_pinned_model() -> SentenceTransformer:
    """Load model từ local cache và dừng nếu revision/dimension không đúng contract."""

    model = SentenceTransformer(
        MODEL_REPOSITORY,
        revision=MODEL_REVISION,
        local_files_only=True,
        device="cpu",
    )
    actual_revision = getattr(model._first_module().auto_model.config, "_commit_hash", None)
    if actual_revision != MODEL_REVISION:
        raise RuntimeError(f"Loaded encoder revision mismatch: {actual_revision}")
    if model.get_embedding_dimension() != EXPECTED_DIMENSION:
        raise RuntimeError("Loaded encoder dimension differs from Phase 6 contract")
    return model


def build_metadata(records: list[dict]) -> list[dict]:
    """Tạo mapping tối thiểu cần cho citation; chunk text vẫn đọc từ canonical Gold."""

    return [
        {
            "index_position": position,
            "chunk_id": record["chunk_id"],
            "video_id": record["video_id"],
            "video_title": record["title"],
            "start_second": record["start_second"],
            "end_second": record["end_second"],
            "source_url": f"https://www.youtube.com/watch?v={record['video_id']}",
        }
        for position, record in enumerate(records)
    ]


def main() -> None:
    """Encode canonical chunks, validate vectors và ghi index/audit artifacts."""

    parser = argparse.ArgumentParser(description="Build exact MIT 6.0001 dense vector index.")
    parser.parse_args()

    torch.manual_seed(0)
    np.random.seed(0)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)

    records, chunking_config, canonical_hash = validated_canonical_input()
    model = load_pinned_model()
    vectors = model.encode(
        [record["chunk_text"] for record in records],
        batch_size=BATCH_SIZE,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    vectors = np.asarray(vectors, dtype=np.float32, order="C")
    if vectors.shape != (EXPECTED_CHUNK_COUNT, EXPECTED_DIMENSION):
        raise ValueError(f"Unexpected embedding shape: {vectors.shape}")

    nonfinite_value_count = int((~np.isfinite(vectors)).sum())
    norms = np.linalg.norm(vectors, axis=1)
    zero_norm_vector_count = int((norms == 0).sum())
    norm_violation_count = int((np.abs(norms - 1.0) > NORM_TOLERANCE).sum())
    if nonfinite_value_count or zero_norm_vector_count or norm_violation_count:
        raise ValueError(
            "Embedding validation failed: "
            f"nonfinite={nonfinite_value_count}, zero_norm={zero_norm_vector_count}, "
            f"norm_violations={norm_violation_count}"
        )

    metadata = build_metadata(records)
    embeddings_bytes = serialize_npy(vectors)
    metadata_bytes = serialize_jsonl(metadata)
    embeddings_hash = sha256_bytes(embeddings_bytes)
    metadata_hash = sha256_bytes(metadata_bytes)
    index_content_hash = sha256_bytes(embeddings_bytes + metadata_bytes)
    chunk_id_order_hash = sha256_bytes(
        canonical_json_bytes([record["chunk_id"] for record in records])
    )

    identity = {
        "index_version": INDEX_VERSION,
        "scope_version": EXPECTED_SCOPE_VERSION,
        "canonical_gold_sha256": canonical_hash,
        "model_repository": MODEL_REPOSITORY,
        "model_revision": MODEL_REVISION,
        "embedding_dimension": EXPECTED_DIMENSION,
        "normalize_embeddings": True,
        "index_content_sha256": index_content_hash,
    }
    index_run_id = f"mit60001_index_{sha256_bytes(canonical_json_bytes(identity))[:16]}"
    runtime_manifest = {
        "$schema": "../../../schemas/runtime_index_manifest_v1.schema.json",
        "schema_version": "runtime_index_manifest_v1",
        "index_run_id": index_run_id,
        **identity,
        "index_backend": "numpy_exact_cosine_v1",
        "similarity": "cosine_via_dot_product_of_l2_normalized_vectors",
        "embedding_dtype": "float32",
        "norm_tolerance": NORM_TOLERANCE,
        "canonical_gold_file": str(CANONICAL_GOLD_FILE).replace("\\", "/"),
        "selected_chunking_config_id": chunking_config["chunking_config_id"],
        "chunk_count": len(records),
        "video_count": len({record["video_id"] for record in records}),
        "chunk_id_order_sha256": chunk_id_order_hash,
        "embeddings_file": str(EMBEDDINGS_FILE).replace("\\", "/"),
        "embeddings_sha256": embeddings_hash,
        "embedding_shape": list(vectors.shape),
        "metadata_file": str(METADATA_FILE).replace("\\", "/"),
        "metadata_sha256": metadata_hash,
        "metadata_record_count": len(metadata),
        "model_max_sequence_length": int(model.max_seq_length),
        "validation_status": "passed",
    }
    schema = json.loads(RUNTIME_MANIFEST_SCHEMA_FILE.read_text(encoding="utf-8"))
    schema_errors = sorted(Draft202012Validator(schema).iter_errors(runtime_manifest), key=lambda error: list(error.path))
    if schema_errors:
        messages = "; ".join(error.message for error in schema_errors)
        raise ValueError(f"Embedding manifest schema validation failed: {messages}")

    write_atomic(EMBEDDINGS_FILE, embeddings_bytes)
    write_atomic(METADATA_FILE, metadata_bytes)
    write_atomic(RUNTIME_MANIFEST_FILE, serialize_runtime_manifest(runtime_manifest))
    print(json.dumps(runtime_manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
