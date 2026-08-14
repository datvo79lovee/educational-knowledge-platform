"""Build exact BM25 lexical index cho canonical MIT 6.0001 Gold chunks.

Index chỉ lưu document metadata, document length và postings; không lặp lại chunk
text. Thứ tự document phải trùng dense index để Hybrid Search có thể fusion theo cùng
``index_position`` mà không cần mapping mơ hồ.
"""

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import platform
from pathlib import Path
import re

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CANONICAL_GOLD_FILE = Path("data/gold/mit_60001/chunks.jsonl")
CANONICAL_MANIFEST_FILE = Path("reports/08_chunking/canonical_gold_manifest.json")
DENSE_MANIFEST_FILE = Path("reports/09_embedding/embedding_index_manifest.json")
LEXICAL_INDEX_FILE = Path("data/indexes/mit_60001/lexical_index.json")
MANIFEST_FILE = Path("reports/10_retrieval/lexical_index_manifest.json")
VALIDATION_FILE = Path("reports/10_retrieval/lexical_index_validation.csv")
MANIFEST_SCHEMA_FILE = Path("schemas/lexical_index_manifest_v1.schema.json")

EXPECTED_SCOPE_VERSION = "mit_60001_fall_2016_v1"
EXPECTED_CONFIG_ID = "semantic_cosine_wp240_v1"
EXPECTED_CHUNK_COUNT = 861
EXPECTED_VIDEO_COUNT = 38
INDEX_VERSION = "mit60001_bm25_v1"
INDEX_BACKEND = "exact_bm25_inverted_index_v1"
TOKENIZER_VERSION = "mit60001_python_lexical_tokenizer_v1"
BM25_K1 = 1.2
BM25_B = 0.75

IDENTIFIER_PATTERN = r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*"
TOKEN_PATTERN = (
    IDENTIFIER_PATTERN
    + r"|\d+(?:\.\d+)?|==|!=|<=|>=|//|\*\*|[+\-*/%<>=]"
)
TOKEN_RE = re.compile(TOKEN_PATTERN)
IDENTIFIER_RE = re.compile(rf"^(?:{IDENTIFIER_PATTERN})$")


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


def serialize_csv(row: dict) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(row))
    writer.writeheader()
    writer.writerow(row)
    return buffer.getvalue().encode("utf-8-sig")


def tokenize(text: str) -> list[str]:
    """Tokenize English/Python text và mở rộng dotted identifier thành components."""

    tokens: list[str] = []
    for match in TOKEN_RE.finditer(text.lower()):
        token = match.group(0)
        tokens.append(token)
        if "." in token and IDENTIFIER_RE.fullmatch(token):
            tokens.extend(token.split("."))
    return tokens


def utc_timestamp(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("--created-at-utc must include timezone")
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def validated_inputs() -> tuple[list[dict], dict, dict, str, str]:
    """Khóa Gold và dense index manifests trước khi tạo lexical index."""

    canonical_manifest = json.loads(CANONICAL_MANIFEST_FILE.read_text(encoding="utf-8"))
    dense_manifest = json.loads(DENSE_MANIFEST_FILE.read_text(encoding="utf-8"))
    canonical_hash = sha256_file(CANONICAL_GOLD_FILE)
    if canonical_hash != canonical_manifest["canonical_output_sha256"]:
        raise ValueError("Canonical Gold hash differs from canonical manifest")
    if canonical_hash != dense_manifest["canonical_gold_sha256"]:
        raise ValueError("Canonical Gold hash differs from dense index manifest")
    if canonical_manifest["validation_status"] != "passed" or dense_manifest["validation_status"] != "passed":
        raise ValueError("Canonical Gold or dense index manifest is not passed")
    if canonical_manifest["selected_chunking_config_id"] != EXPECTED_CONFIG_ID:
        raise ValueError("Canonical Gold does not use the approved chunk configuration")

    records = load_jsonl(CANONICAL_GOLD_FILE)
    chunk_ids = [record["chunk_id"] for record in records]
    if len(records) != EXPECTED_CHUNK_COUNT or len(set(chunk_ids)) != EXPECTED_CHUNK_COUNT:
        raise ValueError("Canonical Gold must contain 861 unique chunk IDs")
    if len({record["video_id"] for record in records}) != EXPECTED_VIDEO_COUNT:
        raise ValueError("Canonical Gold must contain 38 videos")
    if {record["scope_version"] for record in records} != {EXPECTED_SCOPE_VERSION}:
        raise ValueError("Canonical Gold contains a record outside the target scope")
    if {record["chunking_config_id"] for record in records} != {EXPECTED_CONFIG_ID}:
        raise ValueError("Canonical Gold contains a non-selected chunk configuration")

    chunk_id_order_hash = sha256_bytes(canonical_json_bytes(chunk_ids))
    if chunk_id_order_hash != dense_manifest["chunk_id_order_sha256"]:
        raise ValueError("Canonical chunk order differs from dense index order")
    return records, canonical_manifest, dense_manifest, canonical_hash, chunk_id_order_hash


def build_index(records: list[dict], canonical_hash: str, chunk_id_order_hash: str) -> tuple[dict, dict]:
    """Tạo deterministic inverted index và trả cả validation counters."""

    documents = []
    postings: dict[str, list[list[int]]] = defaultdict(list)
    total_token_count = 0
    for position, record in enumerate(records):
        token_counts = Counter(tokenize(record["chunk_text"]))
        document_length = sum(token_counts.values())
        if document_length <= 0:
            raise ValueError(f"Chunk has no lexical token: {record['chunk_id']}")
        documents.append({
            "index_position": position,
            "chunk_id": record["chunk_id"],
            "document_length": document_length,
        })
        total_token_count += document_length
        for token, term_frequency in sorted(token_counts.items()):
            postings[token].append([position, term_frequency])

    posting_records = [
        {
            "token": token,
            "document_frequency": len(postings[token]),
            "postings": postings[token],
        }
        for token in sorted(postings)
    ]
    posting_entry_count = sum(item["document_frequency"] for item in posting_records)
    invalid_document_position_count = sum(
        int(document_position < 0 or document_position >= len(documents))
        for item in posting_records
        for document_position, _ in item["postings"]
    )
    invalid_term_frequency_count = sum(
        int(term_frequency <= 0)
        for item in posting_records
        for _, term_frequency in item["postings"]
    )
    duplicate_posting_document_count = sum(
        len(item["postings"])
        - len({document_position for document_position, _ in item["postings"]})
        for item in posting_records
    )
    if (
        invalid_document_position_count
        or invalid_term_frequency_count
        or duplicate_posting_document_count
    ):
        raise ValueError("Lexical postings validation failed")
    index = {
        "schema_version": "lexical_index_v1",
        "index_version": INDEX_VERSION,
        "scope_version": EXPECTED_SCOPE_VERSION,
        "index_backend": INDEX_BACKEND,
        "canonical_gold_sha256": canonical_hash,
        "chunk_id_order_sha256": chunk_id_order_hash,
        "tokenizer_version": TOKENIZER_VERSION,
        "token_pattern": TOKEN_PATTERN,
        "lowercase": True,
        "dotted_identifier_expansion": True,
        "stemming": False,
        "stopword_removal": False,
        "bm25_k1": BM25_K1,
        "bm25_b": BM25_B,
        "chunk_count": len(documents),
        "vocabulary_size": len(posting_records),
        "total_token_count": total_token_count,
        "average_document_length": total_token_count / len(documents),
        "documents": documents,
        "postings": posting_records,
    }
    validation = {
        "chunk_count": len(documents),
        "unique_chunk_id_count": len({item["chunk_id"] for item in documents}),
        "video_count": len({record["video_id"] for record in records}),
        "vocabulary_size": len(posting_records),
        "total_token_count": total_token_count,
        "minimum_document_length": min(item["document_length"] for item in documents),
        "maximum_document_length": max(item["document_length"] for item in documents),
        "average_document_length": round(total_token_count / len(documents), 9),
        "posting_entry_count": posting_entry_count,
        "invalid_document_position_count": invalid_document_position_count,
        "invalid_term_frequency_count": invalid_term_frequency_count,
        "duplicate_posting_document_count": duplicate_posting_document_count,
    }
    return index, validation


def main() -> None:
    parser = argparse.ArgumentParser(description="Build exact BM25 index for MIT 6.0001 Gold chunks.")
    parser.add_argument(
        "--created-at-utc",
        help="UTC ISO-8601 timestamp; M3 may pin this value for cross-process checks.",
    )
    args = parser.parse_args()
    created_at = utc_timestamp(args.created_at_utc)

    records, canonical_manifest, dense_manifest, canonical_hash, chunk_id_order_hash = validated_inputs()
    index, validation = build_index(records, canonical_hash, chunk_id_order_hash)
    index_bytes = json.dumps(
        index,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8") + b"\n"
    lexical_hash = sha256_bytes(index_bytes)
    identity = {
        "index_version": INDEX_VERSION,
        "scope_version": EXPECTED_SCOPE_VERSION,
        "canonical_gold_sha256": canonical_hash,
        "dense_index_run_id": dense_manifest["index_run_id"],
        "dense_index_content_sha256": dense_manifest["index_content_sha256"],
        "chunk_id_order_sha256": chunk_id_order_hash,
        "tokenizer_version": TOKENIZER_VERSION,
        "bm25_k1": BM25_K1,
        "bm25_b": BM25_B,
        "lexical_index_sha256": lexical_hash,
    }
    index_run_id = f"mit60001_lexical_{sha256_bytes(canonical_json_bytes(identity))[:16]}"
    manifest = {
        "$schema": "../../schemas/lexical_index_manifest_v1.schema.json",
        "schema_version": "lexical_index_manifest_v1",
        "index_run_id": index_run_id,
        "index_created_at_utc": created_at,
        **identity,
        "index_backend": INDEX_BACKEND,
        "canonical_gold_file": str(CANONICAL_GOLD_FILE).replace("\\", "/"),
        "canonical_gold_manifest_file": str(CANONICAL_MANIFEST_FILE).replace("\\", "/"),
        "canonical_gold_manifest_sha256": sha256_file(CANONICAL_MANIFEST_FILE),
        "selected_chunking_config_id": canonical_manifest["selected_chunking_config_id"],
        "dense_index_manifest_file": str(DENSE_MANIFEST_FILE).replace("\\", "/"),
        "dense_index_manifest_sha256": sha256_file(DENSE_MANIFEST_FILE),
        "lexical_index_file": str(LEXICAL_INDEX_FILE).replace("\\", "/"),
        "token_pattern": TOKEN_PATTERN,
        "lowercase": True,
        "dotted_identifier_expansion": True,
        "stemming": False,
        "stopword_removal": False,
        "query_unique_tokens": True,
        "score_dtype": "float64",
        "chunk_count": validation["chunk_count"],
        "video_count": validation["video_count"],
        "vocabulary_size": validation["vocabulary_size"],
        "total_token_count": validation["total_token_count"],
        "minimum_document_length": validation["minimum_document_length"],
        "maximum_document_length": validation["maximum_document_length"],
        "average_document_length": validation["average_document_length"],
        "posting_entry_count": validation["posting_entry_count"],
        "python_version": platform.python_version(),
        "validation_error_count": 0,
        "validation_status": "passed",
    }
    schema = json.loads(MANIFEST_SCHEMA_FILE.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(manifest), key=lambda error: list(error.path))
    if errors:
        raise ValueError(
            "Lexical manifest schema validation failed: "
            + "; ".join(error.message for error in errors)
        )

    validation_row = {
        "index_run_id": index_run_id,
        "canonical_gold_sha256": canonical_hash,
        "dense_index_run_id": dense_manifest["index_run_id"],
        "chunk_id_order_sha256": chunk_id_order_hash,
        **validation,
        "lexical_index_sha256": lexical_hash,
        "manifest_schema_error_count": 0,
        "validation_error_count": 0,
        "validation_status": "passed",
    }
    write_atomic(LEXICAL_INDEX_FILE, index_bytes)
    write_atomic(
        MANIFEST_FILE,
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n",
    )
    write_atomic(VALIDATION_FILE, serialize_csv(validation_row))
    print(json.dumps(validation_row, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
