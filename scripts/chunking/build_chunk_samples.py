"""Build và validate Gold chunk sample hoặc full-corpus experiment."""

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from jsonschema import Draft202012Validator
from sentence_transformers import SentenceTransformer
import sentence_transformers


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SILVER_FILE = Path("data/silver/mit_60001/transcripts_clean.jsonl")
GOLD_SCHEMA_FILE = Path("schemas/gold_chunk_v1.schema.json")
REPORT_DIRECTORY = Path("reports/08_chunking")
SAMPLE_OUTPUT_DIRECTORY = Path("data/gold/mit_60001/samples")
FULL_OUTPUT_DIRECTORY = Path("data/gold/mit_60001/experiments")
SAMPLE_REPORT = REPORT_DIRECTORY / "sample_chunk_validation.csv"
FULL_REPORT = REPORT_DIRECTORY / "full_chunk_validation.csv"
SAMPLE_VIDEO_IDS = {"nykOeWgQcHM", "w4uxYDPsjbw", "FlGjISF3l78", "o9nW0uBqvEo", "6LOwPhPDwVc"}
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
SCHEMA_VERSION = "gold_chunk_v1"
CHUNKING_VERSION = "mit_60001_chunk_v1"


@dataclass(frozen=True)
class Config:
    """Một configuration trong chunking experiment đã được chốt."""

    config_id: str
    strategy: str
    minimum: int
    preferred: int
    maximum: int
    overlap_target: int


CONFIGS = (
    Config("fixed_wp240_o48_v1", "fixed", 192, 240, 240, 48),
    Config("semantic_cosine_wp240_v1", "semantic", 96, 192, 240, 0),
    Config("semantic_cosine_wp192_o32_v1", "semantic", 72, 160, 192, 32),
)


def canonical_bytes(value: dict) -> bytes:
    """Serialize canonical cho content hash theo Gold contract."""

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256(value: bytes) -> str:
    """Trả SHA-256 lowercase."""

    return hashlib.sha256(value).hexdigest()


def derived_text(segments: list[dict]) -> str:
    """Text chỉ dùng cho encoder; Gold text vẫn giữ lossless source text."""

    return re.sub(r"\s+", " ", "\n".join(segment["text"] for segment in segments)).strip()


def token_count(tokenizer, segments: list[dict]) -> int:
    """Đếm word pieces của derived view, không cắt segment để đạt token limit."""

    return len(tokenizer.encode(derived_text(segments), add_special_tokens=False, verbose=False))


def text_token_count(tokenizer, text: str) -> int:
    """Đếm token derived text của một Gold chunk khi tạo run metrics."""

    return len(tokenizer.encode(re.sub(r"\s+", " ", text).strip(), add_special_tokens=False, verbose=False))


def end_second(segment: dict) -> float:
    """Tính end bằng Decimal để tránh artifact float trong JSON output."""

    return float(Decimal(str(segment["start_second"])) + Decimal(str(segment["duration_second"])))


def load_records(mode: str) -> list[dict]:
    """Đọc Silver record theo mode và giữ playlist order."""

    records = [json.loads(line) for line in SILVER_FILE.read_text(encoding="utf-8").splitlines()]
    if mode == "sample":
        selected = [record for record in records if record["video_id"] in SAMPLE_VIDEO_IDS]
        if len(selected) != len(SAMPLE_VIDEO_IDS):
            raise ValueError("Silver sample selection is incomplete")
    elif mode == "full":
        selected = records
        if len(selected) != 38 or len({record["video_id"] for record in selected}) != 38:
            raise ValueError("Full Silver selection must contain 38 unique videos")
    else:
        raise ValueError(f"Unsupported build mode: {mode}")
    return sorted(selected, key=lambda record: record["playlist_position"])


def fixed_ranges(segments: list[dict], config: Config, tokenizer) -> list[tuple[int, int]]:
    """Greedy baseline: đóng chunk trước segment làm vượt hard maximum."""

    ranges, start, index = [], 0, 0
    while index < len(segments):
        candidate = segments[start : index + 1]
        if index > start and token_count(tokenizer, candidate) > config.maximum:
            ranges.append((start, index - 1))
            start = index
        else:
            index += 1
    ranges.append((start, len(segments) - 1))
    return add_overlap(merge_undersize_tail(ranges, segments, config, tokenizer), segments, config, tokenizer)


def semantic_windows(segments: list[dict], tokenizer) -> list[tuple[int, int]]:
    """Tạo window 32–64 word pieces trước khi đo cohesion giữa các window."""

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


def semantic_ranges(segments: list[dict], config: Config, tokenizer, model) -> list[tuple[int, int]]:
    """Chọn boundary cohesion thấp nhất trong vùng token hợp lệ."""

    windows = semantic_windows(segments, tokenizer)
    vectors = model.encode([derived_text(segments[a : b + 1]) for a, b in windows], normalize_embeddings=True)
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
            before_preferred = [i for i in eligible if token_count(tokenizer, segments[windows[window_start][0] : windows[i][1] + 1]) <= config.preferred]
            candidates = before_preferred or eligible
            # Không chọn boundary đẹp về cosine nếu nó tạo non-tail chunk quá nhỏ.
            safe_candidates = []
            for candidate in candidates:
                if candidate == len(windows) - 1:
                    safe_candidates.append(candidate)
                    continue
                remaining_start = windows[candidate + 1][0]
                if token_count(tokenizer, segments[remaining_start:]) >= config.minimum:
                    safe_candidates.append(candidate)
            candidates = safe_candidates or candidates
            chosen = min(candidates, key=lambda i: scores[i] if i < len(scores) else 1.0)
        ranges.append((windows[window_start][0], windows[chosen][1]))
        window_start = chosen + 1
    return add_overlap(merge_undersize_tail(ranges, segments, config, tokenizer), segments, config, tokenizer)


def merge_undersize_tail(ranges: list[tuple[int, int]], segments: list[dict], config: Config, tokenizer) -> list[tuple[int, int]]:
    """Merge tail dưới minimum vào chunk trước nếu union không vượt hard maximum."""

    if len(ranges) < 2:
        return ranges
    tail_start, tail_end = ranges[-1]
    if token_count(tokenizer, segments[tail_start : tail_end + 1]) >= config.minimum:
        return ranges
    previous_start, _ = ranges[-2]
    if token_count(tokenizer, segments[previous_start : tail_end + 1]) > config.maximum:
        return ranges
    return [*ranges[:-2], (previous_start, tail_end)]


def add_overlap(ranges: list[tuple[int, int]], segments: list[dict], config: Config, tokenizer) -> list[tuple[int, int]]:
    """Lùi whole segment ở đầu chunk kế tiếp để tạo overlap gần đúng nếu cần."""

    if not config.overlap_target:
        return ranges
    adjusted = [ranges[0]]
    for start, end in ranges[1:]:
        overlap_start = start
        while overlap_start > 0 and token_count(tokenizer, segments[overlap_start - 1 : start]) < config.overlap_target:
            overlap_start -= 1
        # Overlap là soft target; hard maximum luôn được ưu tiên theo experiment design.
        while overlap_start < start and token_count(tokenizer, segments[overlap_start : end + 1]) > config.maximum:
            overlap_start += 1
        adjusted.append((overlap_start, end))
    return adjusted


def build_chunk(record: dict, config: Config, chunk_index: int, start: int, end: int) -> dict:
    """Tạo một Gold record từ dải Silver segment liên tiếp."""

    segments = record["segments"][start : end + 1]
    text = "\n".join(segment["text"] for segment in segments)
    end_time = end_second(segments[-1])
    hash_input = {"video_id": record["video_id"], "chunking_config_id": config.config_id, "source_segment_start_index": start, "source_segment_end_index": end, "chunk_text": text, "start_second": segments[0]["start_second"], "end_second": end_time}
    return {
        "schema_version": SCHEMA_VERSION, "scope_version": record["scope_version"],
        "silver_schema_version": record["schema_version"], "silver_cleaning_version": record["cleaning_version"],
        "chunking_version": CHUNKING_VERSION, "chunking_config_id": config.config_id,
        "chunk_id": f"{record['video_id']}:{config.config_id}:{chunk_index}",
        "playlist_id": record["playlist_id"], "playlist_position": record["playlist_position"],
        "video_id": record["video_id"], "title": record["title"], "chunk_index": chunk_index,
        "source_segment_start_index": start, "source_segment_end_index": end,
        "source_segment_count": len(segments), "chunk_text": text, "chunk_length": len(text),
        "start_second": segments[0]["start_second"], "end_second": end_time,
        "content_sha256": sha256(canonical_bytes(hash_input)),
        "lineage": {"silver_file": str(SILVER_FILE).replace("\\", "/"), "silver_content_sha256": record["content_sha256"]},
    }


def serialize(records: list[dict]) -> bytes:
    """Serialize JSONL ổn định theo thứ tự tạo record."""

    return b"".join(json.dumps(record, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n" for record in records)


def write_atomic(path: Path, content: bytes) -> None:
    """Chỉ replace output khi nội dung hoàn chỉnh."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_bytes(content)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def build_config(config: Config, model, validator, silver_records: list[dict]) -> tuple[list[dict], dict]:
    """Build một configuration và trả metadata validation summary."""

    records = []
    for silver in silver_records:
        ranges = fixed_ranges(silver["segments"], config, model.tokenizer) if config.strategy == "fixed" else semantic_ranges(silver["segments"], config, model.tokenizer, model)
        for index, (start, end) in enumerate(ranges):
            records.append(build_chunk(silver, config, index, start, end))
    errors = [error.message for record in records for error in validator.iter_errors(record)]
    silver_by_id = {record["video_id"]: record for record in silver_records}
    for record in records:
        silver = silver_by_id[record["video_id"]]
        source = silver["segments"][record["source_segment_start_index"] : record["source_segment_end_index"] + 1]
        expected_text = "\n".join(segment["text"] for segment in source)
        expected_hash_input = {"video_id": record["video_id"], "chunking_config_id": record["chunking_config_id"], "source_segment_start_index": record["source_segment_start_index"], "source_segment_end_index": record["source_segment_end_index"], "chunk_text": expected_text, "start_second": source[0]["start_second"], "end_second": end_second(source[-1])}
        if record["chunk_text"] != expected_text or record["chunk_length"] != len(expected_text):
            errors.append(f"text/length mismatch: {record['chunk_id']}")
        if record["source_segment_count"] != len(source):
            errors.append(f"segment range mismatch: {record['chunk_id']}")
        if record["start_second"] != source[0]["start_second"] or record["end_second"] != end_second(source[-1]):
            errors.append(f"timing mismatch: {record['chunk_id']}")
        if record["lineage"]["silver_content_sha256"] != silver["content_sha256"]:
            errors.append(f"lineage mismatch: {record['chunk_id']}")
        if record["content_sha256"] != sha256(canonical_bytes(expected_hash_input)):
            errors.append(f"content hash mismatch: {record['chunk_id']}")
    covered = {(record["video_id"], index) for record in records for index in range(record["source_segment_start_index"], record["source_segment_end_index"] + 1)}
    expected = {(silver["video_id"], segment["segment_index"]) for silver in silver_records for segment in silver["segments"]}
    duplicate_ids = len(records) - len({record["chunk_id"] for record in records})
    token_counts = [text_token_count(model.tokenizer, record["chunk_text"]) for record in records]
    chunks_per_video = [sum(record["video_id"] == video_id for record in records) for video_id in silver_by_id]
    overlaps = []
    for video_id in silver_by_id:
        video_chunks = [record for record in records if record["video_id"] == video_id]
        for previous, current in zip(video_chunks, video_chunks[1:]):
            start, end = current["source_segment_start_index"], min(previous["source_segment_end_index"], current["source_segment_end_index"])
            overlaps.append(token_count(model.tokenizer, silver_by_id[video_id]["segments"][start : end + 1]) if end >= start else 0)
    non_tail_undersize = 0
    multi_segment_oversize = 0
    for video_id in silver_by_id:
        video_chunks = [record for record in records if record["video_id"] == video_id]
        for record in video_chunks[:-1]:
            count = text_token_count(model.tokenizer, record["chunk_text"])
            if count < config.minimum and not (count > config.maximum and record["source_segment_count"] == 1):
                non_tail_undersize += 1
            if count > config.maximum and record["source_segment_count"] > 1:
                multi_segment_oversize += 1
    summary = {
        "total_chunks": len(records), "source_segment_coverage": len(covered) == len(expected),
        "duplicate_chunk_id_count": duplicate_ids, "schema_error_count": len(errors),
        "chunks_per_video_min": min(chunks_per_video), "chunks_per_video_max": max(chunks_per_video),
        "chunks_per_video_mean": round(sum(chunks_per_video) / len(chunks_per_video), 3),
        "token_count_min": min(token_counts), "token_count_max": max(token_counts),
        "token_count_mean": round(sum(token_counts) / len(token_counts), 3),
        "actual_overlap_token_min": min(overlaps, default=0), "actual_overlap_token_max": max(overlaps, default=0),
        "actual_overlap_token_mean": round(sum(overlaps) / len(overlaps), 3) if overlaps else 0,
        "oversize_single_segment_count": sum(count > config.maximum and record["source_segment_count"] == 1 for count, record in zip(token_counts, records)),
        "undersize_tail_chunk_count": sum(text_token_count(model.tokenizer, record["chunk_text"]) < config.minimum for video_id in silver_by_id for record in [[chunk for chunk in records if chunk["video_id"] == video_id][-1]]),
        "undersize_non_tail_chunk_count": non_tail_undersize,
        "oversize_multi_segment_chunk_count": multi_segment_oversize,
    }
    if errors or covered != expected or duplicate_ids or non_tail_undersize or multi_segment_oversize:
        raise RuntimeError(f"Chunk validation failed for {config.config_id}: {summary}")
    return records, summary


def main() -> None:
    """Build ba configuration, kiểm tra rebuild độc lập và ghi report."""

    parser = argparse.ArgumentParser(description="Build MIT 6.0001 Gold chunk experiments.")
    parser.add_argument("--mode", choices=("sample", "full"), default="sample", help="Build five-video sample or all 38 Silver videos.")
    parser.add_argument("--single-build", action="store_true", help="Skip in-process rebuild; only for cross-process verifier.")
    parser.add_argument("--skip-report", action="store_true", help="Do not overwrite the validation report for the selected mode.")
    args = parser.parse_args()
    model = SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION, local_files_only=True)
    revision = getattr(model._first_module().auto_model.config, "_commit_hash", None)
    if not revision:
        raise RuntimeError("Encoder revision is not pinned in local model metadata")
    schema = json.loads(GOLD_SCHEMA_FILE.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    silver_records = load_records(args.mode)
    output_directory = SAMPLE_OUTPUT_DIRECTORY if args.mode == "sample" else FULL_OUTPUT_DIRECTORY
    report_path = SAMPLE_REPORT if args.mode == "sample" else FULL_REPORT
    rows = []
    for config in CONFIGS:
        first, summary = build_config(config, model, validator, silver_records)
        content = serialize(first)
        deterministic = True
        if not args.single_build:
            second, _ = build_config(config, model, validator, silver_records)
            deterministic = content == serialize(second)
        if not deterministic:
            raise RuntimeError(f"Non-deterministic build: {config.config_id}")
        output = output_directory / config.config_id / "chunks.jsonl"
        write_atomic(output, content)
        rows.append({"chunking_config_id": config.config_id, "encoder_repository": MODEL_NAME, "encoder_revision": revision, "sentence_transformers_version": sentence_transformers.__version__, "tokenizer_name": model.tokenizer.name_or_path, "tokenizer_revision": revision, **summary, "in_process_rebuild_deterministic": deterministic, "output_sha256": sha256(content), "validation_status": "passed"})
    if not args.skip_report:
        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
        write_atomic(report_path, buffer.getvalue().encode("utf-8-sig"))
    print(f"Mode: {args.mode}; videos: {len(silver_records)}; configurations validated: {len(rows)}")


if __name__ == "__main__":
    main()
