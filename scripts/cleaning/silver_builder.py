"""Shared core để build Silver transcript theo contract và Cleaning Policy v1.

Core không chọn sample hay full corpus. Caller truyền tập video ID đã duyệt và
đường dẫn output; vì vậy sample và full build sẽ dùng cùng một logic.
"""

import csv
import hashlib
import io
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


SCOPE_VERSION = "mit_60001_fall_2016_v1"
SCHEMA_VERSION = "silver_transcript_v1"
CLEANING_VERSION = "mit_60001_clean_v1"
PLAYLIST_ID = "PLUl4u3cNGP63WbdFxL8giv4yhgdMGaZNA"
FULL_TARGET_RECORD_COUNT = 38

MANIFEST_FILE = Path("reports/04_scope_decision/target_manifest.csv")
BRONZE_FILE = Path("data/bronze/transcripts_raw.jsonl")
JSON_SCHEMA_FILE = Path("schemas/silver_transcript_v1.schema.json")


@dataclass(frozen=True)
class ValidationResult:
    """Kết quả có cấu trúc cho một Silver record.

    Report đọc trực tiếp boolean thay vì suy luận trạng thái từ wording của error.
    """

    schema_valid: bool
    manifest_metadata_valid: bool
    bronze_text_equal: bool
    timing_equal: bool
    source_hash_valid: bool
    content_hash_valid: bool
    invariant_valid: bool
    errors: tuple[str, ...]

    @property
    def passed(self) -> bool:
        """Record chỉ pass khi mọi nhóm kiểm tra đều pass."""

        return (
            self.schema_valid
            and self.manifest_metadata_valid
            and self.bronze_text_equal
            and self.timing_equal
            and self.source_hash_valid
            and self.content_hash_valid
            and self.invariant_valid
        )


@dataclass(frozen=True)
class BuildArtifacts:
    """Output in-memory của một lần build độc lập từ manifest và Bronze."""

    records: list[dict]
    validation_results: dict[str, ValidationResult]
    output_bytes: bytes


def strip_line_ending(raw_line: bytes) -> bytes:
    """Chỉ bỏ line ending JSONL trước khi tính source payload hash."""

    if raw_line.endswith(b"\r\n"):
        return raw_line[:-2]
    if raw_line.endswith(b"\n"):
        return raw_line[:-1]
    return raw_line


def sha256_hex(value: bytes) -> str:
    """Trả SHA-256 lowercase theo Silver contract."""

    return hashlib.sha256(value).hexdigest()


def canonical_json_bytes(value: dict) -> bytes:
    """Serialize input hash theo quy tắc canonical đã ghi trong contract."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def load_manifest_rows(selected_video_ids: set[str] | None) -> list[dict]:
    """Đọc manifest v1 và chọn IDs theo playlist order.

    ``None`` nghĩa là toàn bộ target manifest. Sample caller truyền một tập năm ID.
    """

    with MANIFEST_FILE.open("r", encoding="utf-8-sig", newline="") as file:
        manifest_rows = list(csv.DictReader(file))

    manifest_ids = [row["video_id"] for row in manifest_rows]
    if len(manifest_ids) != len(set(manifest_ids)):
        raise ValueError("Target manifest contains duplicate video_id")
    if any(
        row["scope_version"] != SCOPE_VERSION
        or row["playlist_id"] != PLAYLIST_ID
        or row["included"] != "True"
        for row in manifest_rows
    ):
        raise ValueError("Target manifest does not match Silver v1 scope")

    available_ids = set(manifest_ids)
    selected_ids = available_ids if selected_video_ids is None else selected_video_ids
    outside_scope = selected_ids - available_ids
    if outside_scope:
        raise ValueError(f"Selected IDs outside manifest: {sorted(outside_scope)}")

    rows = [row for row in manifest_rows if row["video_id"] in selected_ids]
    if len(rows) != len(selected_ids):
        raise ValueError("Manifest selection is incomplete")
    return sorted(rows, key=lambda row: int(row["playlist_position"]))


def load_bronze_payloads(selected_video_ids: set[str]) -> dict[str, tuple[dict, bytes]]:
    """Đọc raw JSONL lines cho selection và giữ byte nguồn để hash lineage."""

    payloads_by_id = {}
    with BRONZE_FILE.open("rb") as file:
        for line_number, raw_line in enumerate(file, start=1):
            source_line = strip_line_ending(raw_line)
            try:
                payload = json.loads(source_line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ValueError(
                    f"Invalid Bronze JSON at line {line_number}: {error}"
                ) from error

            video_id = payload.get("video_id")
            if video_id not in selected_video_ids:
                continue
            if video_id in payloads_by_id:
                raise ValueError(f"Duplicate Bronze payload: {video_id}")
            payloads_by_id[video_id] = (payload, source_line)

    missing_ids = selected_video_ids - set(payloads_by_id)
    if missing_ids:
        raise ValueError(f"Missing Bronze payloads: {sorted(missing_ids)}")
    return payloads_by_id


def load_schema_validator() -> Draft202012Validator:
    """Load JSON Schema v1 và bật date-time format validation."""

    with JSON_SCHEMA_FILE.open("r", encoding="utf-8") as file:
        schema = json.load(file)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def build_content_hash(video_id: str, language_code: str, segments: list[dict]) -> str:
    """Hash cleaned text và timing để phát hiện content drift."""

    hash_input = {
        "video_id": video_id,
        "language_code": language_code,
        "segments": [
            {
                "duration_second": segment["duration_second"],
                "source_segment_index": segment["source_segment_index"],
                "start_second": segment["start_second"],
                "text": segment["text"],
            }
            for segment in segments
        ],
    }
    return sha256_hex(canonical_json_bytes(hash_input))


def build_record(manifest_row: dict, payload: dict, source_line: bytes) -> dict:
    """Map một Bronze payload thành Silver record lossless v1."""

    required_fields = {
        "video_id",
        "language_code",
        "language",
        "is_generated",
        "segments",
        "fetched_at",
    }
    missing_fields = required_fields - set(payload)
    if missing_fields:
        raise ValueError(
            f"Payload {manifest_row['video_id']} missing fields: {sorted(missing_fields)}"
        )
    if payload["video_id"] != manifest_row["video_id"]:
        raise ValueError("Manifest and Bronze video_id do not match")
    if not isinstance(payload["segments"], list) or not payload["segments"]:
        raise ValueError(f"Payload {payload['video_id']} has no segments")

    silver_segments = []
    previous_start = None
    for source_index, bronze_segment in enumerate(payload["segments"]):
        text = bronze_segment.get("text")
        start = bronze_segment.get("start")
        duration = bronze_segment.get("duration")

        if not isinstance(text, str) or not text.strip():
            raise ValueError(
                f"Payload {payload['video_id']} has empty text at {source_index}"
            )
        if not isinstance(start, (int, float)) or isinstance(start, bool) or start < 0:
            raise ValueError(
                f"Payload {payload['video_id']} has invalid start at {source_index}"
            )
        if (
            not isinstance(duration, (int, float))
            or isinstance(duration, bool)
            or duration <= 0
        ):
            raise ValueError(
                f"Payload {payload['video_id']} has invalid duration at {source_index}"
            )
        if previous_start is not None and start < previous_start:
            raise ValueError(
                f"Payload {payload['video_id']} has out-of-order timing at {source_index}"
            )

        # Lossless policy: copy nguyên text và timing, không normalize hoặc deduplicate.
        silver_segments.append(
            {
                "segment_index": source_index,
                "source_segment_index": source_index,
                "text": text,
                "start_second": start,
                "duration_second": duration,
            }
        )
        previous_start = start

    transcript_text = "\n".join(segment["text"] for segment in silver_segments)
    return {
        "schema_version": SCHEMA_VERSION,
        "scope_version": SCOPE_VERSION,
        "cleaning_version": CLEANING_VERSION,
        "playlist_id": PLAYLIST_ID,
        "playlist_position": int(manifest_row["playlist_position"]),
        "video_id": payload["video_id"],
        "title": manifest_row["title"],
        "language_code": payload["language_code"],
        "language_name": payload["language"],
        "is_generated": payload["is_generated"],
        "fetched_at": payload["fetched_at"],
        "segment_count": len(silver_segments),
        "transcript_text": transcript_text,
        "transcript_length": len(transcript_text),
        "content_sha256": build_content_hash(
            payload["video_id"], payload["language_code"], silver_segments
        ),
        "lineage": {
            "bronze_file": str(BRONZE_FILE).replace("\\", "/"),
            "manifest_file": str(MANIFEST_FILE).replace("\\", "/"),
            "source_payload_sha256": sha256_hex(source_line),
        },
        "segments": silver_segments,
    }


def validate_record(
    record: dict,
    manifest_row: dict,
    payload: dict,
    source_line: bytes,
    validator: Draft202012Validator,
) -> ValidationResult:
    """Validate record và trả boolean có cấu trúc cùng error detail."""

    errors = []
    schema_valid = True
    manifest_metadata_valid = True
    bronze_text_equal = True
    timing_equal = True
    source_hash_valid = True
    content_hash_valid = True
    invariant_valid = True

    for error in sorted(validator.iter_errors(record), key=str):
        schema_valid = False
        errors.append(f"schema: {error.message}")

    metadata_pairs = {
        "playlist_position": (record["playlist_position"], int(manifest_row["playlist_position"])),
        "title": (record["title"], manifest_row["title"]),
        "video_id": (record["video_id"], payload["video_id"]),
        "language_code": (record["language_code"], payload["language_code"]),
        "language_name": (record["language_name"], payload["language"]),
        "is_generated": (record["is_generated"], payload["is_generated"]),
        "fetched_at": (record["fetched_at"], payload["fetched_at"]),
    }
    for field_name, (actual, expected) in metadata_pairs.items():
        if actual != expected:
            manifest_metadata_valid = False
            errors.append(f"metadata mismatch: {field_name}")

    try:
        fetched_at = datetime.fromisoformat(record["fetched_at"].replace("Z", "+00:00"))
        if fetched_at.tzinfo is None:
            invariant_valid = False
            errors.append("invariant: fetched_at has no timezone")
    except (AttributeError, TypeError, ValueError):
        invariant_valid = False
        errors.append("invariant: fetched_at is not ISO-8601")

    if record["segment_count"] != len(record["segments"]):
        invariant_valid = False
        errors.append("invariant: segment_count differs from Silver segments")
    if record["segment_count"] != len(payload["segments"]):
        invariant_valid = False
        errors.append("invariant: segment_count differs from Bronze segments")

    expected_texts = []
    previous_start = None
    for expected_index, (silver_segment, bronze_segment) in enumerate(
        zip(record["segments"], payload["segments"])
    ):
        if silver_segment["segment_index"] != expected_index:
            invariant_valid = False
            errors.append(f"invariant: segment_index at {expected_index}")
        if silver_segment["source_segment_index"] != expected_index:
            invariant_valid = False
            errors.append(f"invariant: source_segment_index at {expected_index}")
        if silver_segment["text"] != bronze_segment["text"]:
            bronze_text_equal = False
            errors.append(f"bronze_text mismatch at {expected_index}")
        if (
            silver_segment["start_second"] != bronze_segment["start"]
            or silver_segment["duration_second"] != bronze_segment["duration"]
        ):
            timing_equal = False
            errors.append(f"timing mismatch at {expected_index}")
        if not silver_segment["text"].strip():
            invariant_valid = False
            errors.append(f"invariant: empty text at {expected_index}")
        if previous_start is not None and silver_segment["start_second"] < previous_start:
            invariant_valid = False
            errors.append(f"invariant: out-of-order start at {expected_index}")
        previous_start = silver_segment["start_second"]
        expected_texts.append(bronze_segment["text"])

    expected_transcript_text = "\n".join(expected_texts)
    if record["transcript_text"] != expected_transcript_text:
        bronze_text_equal = False
        errors.append("bronze_text mismatch: transcript_text")
    if record["transcript_length"] != len(record["transcript_text"]):
        invariant_valid = False
        errors.append("invariant: transcript_length")

    if record["lineage"]["source_payload_sha256"] != sha256_hex(source_line):
        source_hash_valid = False
        errors.append("source_hash mismatch")
    if record["content_sha256"] != build_content_hash(
        record["video_id"], record["language_code"], record["segments"]
    ):
        content_hash_valid = False
        errors.append("content_hash mismatch")

    return ValidationResult(
        schema_valid=schema_valid,
        manifest_metadata_valid=manifest_metadata_valid,
        bronze_text_equal=bronze_text_equal,
        timing_equal=timing_equal,
        source_hash_valid=source_hash_valid,
        content_hash_valid=content_hash_valid,
        invariant_valid=invariant_valid,
        errors=tuple(errors),
    )


def serialize_jsonl(records: list[dict]) -> bytes:
    """Serialize record theo key insertion order để output byte-stable."""

    return b"".join(
        json.dumps(
            record,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
        for record in records
    )


def build_artifacts(selected_video_ids: set[str] | None) -> BuildArtifacts:
    """Thực hiện một build độc lập: đọc lại manifest, Bronze, schema rồi validate."""

    manifest_rows = load_manifest_rows(selected_video_ids)
    selected_ids = {row["video_id"] for row in manifest_rows}

    # ``None`` là đường chạy full corpus. Contract v1 khóa chính xác 38 video
    # ở position 0..37; không cho manifest drift âm thầm qua lần build sau.
    if selected_video_ids is None:
        positions = [int(row["playlist_position"]) for row in manifest_rows]
        if len(manifest_rows) != FULL_TARGET_RECORD_COUNT:
            raise ValueError(
                "Full Silver build requires exactly "
                f"{FULL_TARGET_RECORD_COUNT} manifest records"
            )
        if positions != list(range(FULL_TARGET_RECORD_COUNT)):
            raise ValueError("Full Silver manifest positions must be contiguous 0..37")

    payloads_by_id = load_bronze_payloads(selected_ids)
    validator = load_schema_validator()

    records = []
    validation_results = {}
    for manifest_row in manifest_rows:
        payload, source_line = payloads_by_id[manifest_row["video_id"]]
        record = build_record(manifest_row, payload, source_line)
        records.append(record)
        validation_results[record["video_id"]] = validate_record(
            record,
            manifest_row,
            payload,
            source_line,
            validator,
        )

    if {record["video_id"] for record in records} != selected_ids:
        raise RuntimeError("Build output IDs differ from selected IDs")
    return BuildArtifacts(
        records=records,
        validation_results=validation_results,
        output_bytes=serialize_jsonl(records),
    )


def write_bytes_atomically(path: Path, content: bytes) -> None:
    """Ghi qua file tạm và chỉ replace output khi content hoàn chỉnh."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() == content:
        return

    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    try:
        temporary_path.write_bytes(content)
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def write_validation_report(
    report_path: Path,
    artifacts: BuildArtifacts,
    in_process_rebuild_deterministic: bool,
) -> None:
    """Ghi CSV structured validation, không chứa transcript hoặc segment text."""

    rows = []
    for record in artifacts.records:
        result = artifacts.validation_results[record["video_id"]]
        rows.append(
            {
                "scope_version": SCOPE_VERSION,
                "cleaning_version": CLEANING_VERSION,
                "playlist_position": record["playlist_position"],
                "video_id": record["video_id"],
                "title": record["title"],
                "language_code": record["language_code"],
                "language_name": record["language_name"],
                "is_generated": record["is_generated"],
                "segment_count": record["segment_count"],
                "transcript_length": record["transcript_length"],
                "schema_valid": result.schema_valid,
                "manifest_metadata_valid": result.manifest_metadata_valid,
                "bronze_text_equal": result.bronze_text_equal,
                "timing_equal": result.timing_equal,
                "source_hash_valid": result.source_hash_valid,
                "content_hash_valid": result.content_hash_valid,
                "invariant_valid": result.invariant_valid,
                "in_process_rebuild_deterministic": in_process_rebuild_deterministic,
                "validation_status": "passed" if result.passed else "failed",
                "error_count": len(result.errors),
            }
        )

    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    write_bytes_atomically(report_path, buffer.getvalue().encode("utf-8-sig"))


def build_silver(
    selected_video_ids: set[str] | None,
    output_path: Path,
    report_path: Path,
) -> BuildArtifacts:
    """Build selection qua shared core và kiểm tra hai rebuild độc lập trong process."""

    first_build = build_artifacts(selected_video_ids)
    second_build = build_artifacts(selected_video_ids)
    in_process_rebuild_deterministic = (
        first_build.output_bytes == second_build.output_bytes
    )

    if not in_process_rebuild_deterministic:
        raise RuntimeError("Independent in-process builds produced different bytes")

    write_validation_report(
        report_path,
        first_build,
        in_process_rebuild_deterministic,
    )
    failures = {
        video_id: result.errors
        for video_id, result in first_build.validation_results.items()
        if not result.passed
    }
    if failures:
        raise RuntimeError(f"Silver validation failed: {failures}")

    write_bytes_atomically(output_path, first_build.output_bytes)
    return first_build
