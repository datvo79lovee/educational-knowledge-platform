"""Build canonical MIT 6.0001 Gold directly from Silver and a frozen config.

This is the public rebuild path.  It deliberately has no dependency on the
historical configuration review, promotion decision, reports/08, or experiment
outputs.  Those artifacts document how the config was selected; they are not
inputs to a rebuild.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from jsonschema import Draft202012Validator
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_CONFIG = PROJECT_ROOT / "config/mit_60001_canonical_chunking.json"
DEFAULT_SILVER = PROJECT_ROOT / "data/silver/mit_60001/transcripts_clean.jsonl"
DEFAULT_OUTPUT = PROJECT_ROOT / "data/gold/mit_60001/chunks.jsonl"
GOLD_SCHEMA = PROJECT_ROOT / "schemas/gold_chunk_v1.schema.json"


@dataclass(frozen=True)
class ChunkingConfig:
    config_id: str
    minimum: int
    preferred: int
    maximum: int
    overlap_target: int
    encoder_repository: str
    encoder_revision: str
    chunking_version: str


def canonical_bytes(value: dict) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def end_second(segment: dict) -> float:
    return float(Decimal(str(segment["start_second"])) + Decimal(str(segment["duration_second"])))


def derived_text(segments: list[dict]) -> str:
    return re.sub(r"\s+", " ", "\n".join(segment["text"] for segment in segments)).strip()


def token_count(tokenizer, segments: list[dict]) -> int:
    return len(tokenizer.encode(derived_text(segments), add_special_tokens=False, verbose=False))


def read_config(path: Path) -> ChunkingConfig:
    value = json.loads(path.read_text(encoding="utf-8"))
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
    if set(value) != required or value["schema_version"] != "canonical_chunking_config_v1":
        raise ValueError("Invalid canonical chunking config shape")
    if value["scope_version"] != "mit_60001_fall_2016_v1":
        raise ValueError("Unsupported chunking scope")
    if value["strategy"] != "semantic_cosine":
        raise ValueError("Canonical builder only supports semantic_cosine")
    encoder = value["encoder"]
    if set(encoder) != {"repository", "revision"}:
        raise ValueError("Invalid encoder identity")
    minimum, preferred, maximum = (
        value["minimum_wordpieces"],
        value["preferred_wordpieces"],
        value["maximum_wordpieces"],
    )
    if not all(isinstance(item, int) and item > 0 for item in (minimum, preferred, maximum)):
        raise ValueError("Chunk sizes must be positive integers")
    if not minimum <= preferred <= maximum or value["overlap_target_wordpieces"] != 0:
        raise ValueError("Unsupported canonical chunking bounds")
    return ChunkingConfig(
        config_id=value["chunking_config_id"],
        minimum=minimum,
        preferred=preferred,
        maximum=maximum,
        overlap_target=value["overlap_target_wordpieces"],
        encoder_repository=encoder["repository"],
        encoder_revision=encoder["revision"],
        chunking_version=value["chunking_version"],
    )


def load_silver(path: Path) -> list[dict]:
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if len(records) != 38 or len({record["video_id"] for record in records}) != 38:
        raise ValueError("Full MIT 6.0001 Silver corpus must contain 38 unique videos")
    return sorted(records, key=lambda record: record["playlist_position"])


def semantic_windows(segments: list[dict], tokenizer) -> list[tuple[int, int]]:
    windows, start, index = [], 0, 0
    while index < len(segments):
        candidate = segments[start : index + 1]
        count = token_count(tokenizer, candidate)
        if index > start and count > 64:
            windows.append((start, index - 1))
            start = index
        else:
            index += 1
            if count >= 32:
                windows.append((start, index - 1))
                start = index
    if start < len(segments):
        windows.append((start, len(segments) - 1))
    return windows


def merge_undersize_tail(
    ranges: list[tuple[int, int]], segments: list[dict], config: ChunkingConfig, tokenizer
) -> list[tuple[int, int]]:
    if len(ranges) < 2:
        return ranges
    tail_start, tail_end = ranges[-1]
    if token_count(tokenizer, segments[tail_start : tail_end + 1]) >= config.minimum:
        return ranges
    previous_start, _ = ranges[-2]
    if token_count(tokenizer, segments[previous_start : tail_end + 1]) > config.maximum:
        return ranges
    return [*ranges[:-2], (previous_start, tail_end)]


def semantic_ranges(segments: list[dict], config: ChunkingConfig, tokenizer, model) -> list[tuple[int, int]]:
    windows = semantic_windows(segments, tokenizer)
    vectors = model.encode(
        [derived_text(segments[start : end + 1]) for start, end in windows],
        normalize_embeddings=True,
    )
    scores = [float((vectors[index] * vectors[index + 1]).sum()) for index in range(len(vectors) - 1)]
    ranges, window_start = [], 0
    while window_start < len(windows):
        eligible = []
        for window_end in range(window_start, len(windows)):
            start, end = windows[window_start][0], windows[window_end][1]
            count = token_count(tokenizer, segments[start : end + 1])
            if count > config.maximum and window_end > window_start:
                break
            if count >= config.minimum:
                eligible.append(window_end)
        if not eligible:
            chosen = window_start
        else:
            before_preferred = [
                index
                for index in eligible
                if token_count(tokenizer, segments[windows[window_start][0] : windows[index][1] + 1])
                <= config.preferred
            ]
            candidates = before_preferred or eligible
            safe_candidates = []
            for candidate in candidates:
                if candidate == len(windows) - 1:
                    safe_candidates.append(candidate)
                elif token_count(tokenizer, segments[windows[candidate + 1][0] :]) >= config.minimum:
                    safe_candidates.append(candidate)
            candidates = safe_candidates or candidates
            chosen = min(candidates, key=lambda index: scores[index] if index < len(scores) else 1.0)
        ranges.append((windows[window_start][0], windows[chosen][1]))
        window_start = chosen + 1
    return merge_undersize_tail(ranges, segments, config, tokenizer)


def build_chunk(record: dict, config: ChunkingConfig, chunk_index: int, start: int, end: int) -> dict:
    segments = record["segments"][start : end + 1]
    text = "\n".join(segment["text"] for segment in segments)
    end_time = end_second(segments[-1])
    hash_input = {
        "video_id": record["video_id"],
        "chunking_config_id": config.config_id,
        "source_segment_start_index": start,
        "source_segment_end_index": end,
        "chunk_text": text,
        "start_second": segments[0]["start_second"],
        "end_second": end_time,
    }
    return {
        "schema_version": "gold_chunk_v1",
        "scope_version": record["scope_version"],
        "silver_schema_version": record["schema_version"],
        "silver_cleaning_version": record["cleaning_version"],
        "chunking_version": config.chunking_version,
        "chunking_config_id": config.config_id,
        "chunk_id": f"{record['video_id']}:{config.config_id}:{chunk_index}",
        "playlist_id": record["playlist_id"],
        "playlist_position": record["playlist_position"],
        "video_id": record["video_id"],
        "title": record["title"],
        "chunk_index": chunk_index,
        "source_segment_start_index": start,
        "source_segment_end_index": end,
        "source_segment_count": len(segments),
        "chunk_text": text,
        "chunk_length": len(text),
        "start_second": segments[0]["start_second"],
        "end_second": end_time,
        "content_sha256": sha256(canonical_bytes(hash_input)),
        "lineage": {
            "silver_file": "data/silver/mit_60001/transcripts_clean.jsonl",
            "silver_content_sha256": record["content_sha256"],
        },
    }


def serialize(records: list[dict]) -> bytes:
    return b"".join(
        json.dumps(record, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"
        for record in records
    )


def validate_records(records: list[dict], silver_records: list[dict], config: ChunkingConfig) -> None:
    schema = json.loads(GOLD_SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = [error.message for record in records for error in validator.iter_errors(record)]
    silver_by_id = {record["video_id"]: record for record in silver_records}
    expected_coverage = {
        (record["video_id"], segment["segment_index"])
        for record in silver_records
        for segment in record["segments"]
    }
    actual_coverage = set()
    for record in records:
        silver = silver_by_id.get(record["video_id"])
        start, end = record["source_segment_start_index"], record["source_segment_end_index"]
        if silver is None or start < 0 or end < start or end >= len(silver["segments"]):
            errors.append(f"invalid Silver range: {record['chunk_id']}")
            continue
        source = silver["segments"][start : end + 1]
        expected_text = "\n".join(segment["text"] for segment in source)
        expected_hash = sha256(canonical_bytes({
            "video_id": record["video_id"], "chunking_config_id": config.config_id,
            "source_segment_start_index": start, "source_segment_end_index": end,
            "chunk_text": expected_text, "start_second": source[0]["start_second"],
            "end_second": end_second(source[-1]),
        }))
        if (
            record["chunking_config_id"] != config.config_id
            or record["chunk_text"] != expected_text
            or record["chunk_length"] != len(expected_text)
            or record["source_segment_count"] != len(source)
            or record["start_second"] != source[0]["start_second"]
            or record["end_second"] != end_second(source[-1])
            or record["content_sha256"] != expected_hash
            or record["lineage"]["silver_content_sha256"] != silver["content_sha256"]
        ):
            errors.append(f"lineage/content mismatch: {record['chunk_id']}")
        actual_coverage.update((record["video_id"], index) for index in range(start, end + 1))
    if len(records) != len({record["chunk_id"] for record in records}):
        errors.append("duplicate chunk IDs")
    for video_id in silver_by_id:
        indexes = sorted(record["chunk_index"] for record in records if record["video_id"] == video_id)
        if indexes != list(range(len(indexes))):
            errors.append(f"non-contiguous chunk indexes: {video_id}")
    if actual_coverage != expected_coverage:
        errors.append("Silver segment coverage mismatch")
    if errors:
        raise RuntimeError("Canonical Gold validation failed: " + "; ".join(errors[:5]))


def write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_bytes(content)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def build(config: ChunkingConfig, silver_records: list[dict], model) -> list[dict]:
    records = []
    for silver in silver_records:
        for chunk_index, (start, end) in enumerate(semantic_ranges(silver["segments"], config, model.tokenizer, model)):
            records.append(build_chunk(silver, config, chunk_index, start, end))
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Build canonical Gold directly from Silver.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--silver", type=Path, default=DEFAULT_SILVER)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    config = read_config(args.config)
    model = SentenceTransformer(config.encoder_repository, revision=config.encoder_revision, local_files_only=True)
    loaded_revision = getattr(model._first_module().auto_model.config, "_commit_hash", None)
    if loaded_revision != config.encoder_revision:
        raise RuntimeError("Local encoder revision does not match canonical chunking config")
    silver_records = load_silver(args.silver)
    first = build(config, silver_records, model)
    validate_records(first, silver_records, config)
    content = serialize(first)
    second = build(config, silver_records, model)
    if content != serialize(second):
        raise RuntimeError("Canonical Gold rebuild is not deterministic in-process")
    write_atomic(args.output, content)
    print(json.dumps({
        "validation_status": "passed",
        "config": str(args.config.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "silver": str(args.silver.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "output": str(args.output.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "total_chunks": len(first),
        "output_sha256": sha256(content),
        "in_process_deterministic": True,
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
