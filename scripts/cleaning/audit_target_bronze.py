"""Audit cấu trúc Bronze transcript của target corpus MIT 6.0001.

Script chỉ đọc manifest và Bronze JSONL. Ba CSV đầu ra mô tả schema, từng payload
và các chỉ số tổng hợp; không CSV nào chứa nội dung transcript hoặc segment text.
"""

import csv
import html
import io
import json
import re
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path


SCOPE_VERSION = "mit_60001_fall_2016_v1"
EXPECTED_TARGET_VIDEOS = 38

MANIFEST_FILE = Path("reports/04_scope_decision/target_manifest.csv")
BRONZE_FILE = Path("data/bronze/transcripts_raw.jsonl")
REPORTS_DIR = Path("reports/07_cleaning")

SCHEMA_REPORT = REPORTS_DIR / "bronze_schema_audit.csv"
PAYLOAD_REPORT = REPORTS_DIR / "bronze_payload_profile.csv"
SUMMARY_REPORT = REPORTS_DIR / "bronze_audit_summary.csv"

PAYLOAD_SCHEMA = {
    "video_id": "string",
    "language_code": "string",
    "language": "string",
    "is_generated": "boolean",
    "segments": "array",
    "fetched_at": "string",
}

SEGMENT_SCHEMA = {
    "text": "string",
    "start": "number",
    "duration": "number",
}

# Đây chỉ là tín hiệu chọn sample code-heavy, không phải bộ sửa code tự động.
PYTHON_CODE_SIGNAL = re.compile(
    r"\b(?:def|return|for|while|if|else|elif|class|import|lambda|print)\b"
    r"|==|!=|<=|>=|\+=|-=|\*=|/=",
    flags=re.IGNORECASE,
)
BRACKET_ONLY_CUE = re.compile(r"\s*\[[^\]]+\]\s*")
PARENTHETICAL_ONLY_CUE = re.compile(r"\s*\([^\)]+\)\s*")
HTML_TAG = re.compile(r"<[^>]+>")


def type_name(value) -> str:
    """Đổi Python type thành tên ổn định dùng trong schema report."""

    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, (int, float)):
        return "number"
    if value is None:
        return "null"
    return type(value).__name__


def load_manifest() -> list[dict]:
    """Đọc manifest v1 và kiểm tra số lượng, scope, position cùng video trùng."""

    with MANIFEST_FILE.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    if len(rows) != EXPECTED_TARGET_VIDEOS:
        raise ValueError(
            f"Expected {EXPECTED_TARGET_VIDEOS} manifest rows, found {len(rows)}"
        )

    video_ids = [row["video_id"] for row in rows]
    duplicates = [
        video_id
        for video_id, count in Counter(video_ids).items()
        if count > 1
    ]
    if duplicates:
        raise ValueError(f"Duplicate video IDs in manifest: {duplicates}")

    positions = sorted(int(row["playlist_position"]) for row in rows)
    if positions != list(range(EXPECTED_TARGET_VIDEOS)):
        raise ValueError(f"Unexpected playlist positions: {positions}")

    invalid_scope = [
        row["video_id"]
        for row in rows
        if row["scope_version"] != SCOPE_VERSION
    ]
    if invalid_scope:
        raise ValueError(f"Unexpected scope version: {invalid_scope}")

    return sorted(rows, key=lambda row: int(row["playlist_position"]))


def load_target_payloads(target_ids: set[str]) -> list[dict]:
    """Đọc Bronze JSONL và chỉ giữ payload thuộc target manifest."""

    payloads = []
    with BRONZE_FILE.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Invalid Bronze JSON at line {line_number}: {error}"
                ) from error

            if payload.get("video_id") in target_ids:
                payloads.append(payload)

    payload_ids = [payload.get("video_id") for payload in payloads]
    duplicates = [
        video_id
        for video_id, count in Counter(payload_ids).items()
        if count > 1
    ]
    missing = sorted(target_ids - set(payload_ids))

    if duplicates:
        raise ValueError(f"Duplicate target payloads: {duplicates}")
    if missing:
        raise ValueError(f"Missing target payloads: {missing}")
    if len(payloads) != EXPECTED_TARGET_VIDEOS:
        raise ValueError(
            f"Expected {EXPECTED_TARGET_VIDEOS} target payloads, found {len(payloads)}"
        )

    return payloads


def field_profile(
    records: list[dict],
    schema: dict[str, str],
    level: str,
) -> tuple[list[dict], list[str]]:
    """Đếm độ phủ và kiểu dữ liệu của các field bắt buộc ở một schema level."""

    rows = []
    failures = []
    total_records = len(records)

    for field_name, expected_type in schema.items():
        values = [record[field_name] for record in records if field_name in record]
        observed_types = sorted({type_name(value) for value in values})
        missing_count = total_records - len(values)
        empty_count = sum(
            value is None
            or value == ""
            or (isinstance(value, list) and not value)
            for value in values
        )
        invalid_type_count = sum(
            type_name(value) != expected_type for value in values
        )
        status = (
            "passed"
            if missing_count == 0 and empty_count == 0 and invalid_type_count == 0
            else "failed"
        )

        rows.append(
            {
                "scope_version": SCOPE_VERSION,
                "level": level,
                "field_name": field_name,
                "expected_type": expected_type,
                "observed_types": ",".join(observed_types),
                "total_records": total_records,
                "present_count": len(values),
                "missing_count": missing_count,
                "empty_count": empty_count,
                "invalid_type_count": invalid_type_count,
                "status": status,
            }
        )

        if status == "failed":
            failures.append(
                f"{level}.{field_name}: missing={missing_count}, "
                f"empty={empty_count}, invalid_type={invalid_type_count}"
            )

    return rows, failures


def profile_payload(manifest_row: dict, payload: dict) -> tuple[dict, list[str]]:
    """Tính các chỉ số cấu trúc, timing và whitespace cho một target payload."""

    failures = []
    segments = payload["segments"]
    empty_segments = 0
    leading_or_trailing_whitespace = 0
    multiline_segments = 0
    invalid_start = 0
    nonpositive_duration = 0
    out_of_order_segments = 0
    overlapping_segments = 0
    code_signal_count = 0
    cleaned_texts = []
    normalized_texts = []
    maximum_end_second = 0.0
    previous_start = None
    previous_end = None
    contains_cr_segments = 0
    contains_tab_segments = 0
    contains_nbsp_segments = 0
    contains_zero_width_segments = 0
    contains_replacement_character_segments = 0
    non_nfc_segments = 0
    multiple_ascii_space_segments = 0
    line_with_edge_whitespace_segments = 0
    bracket_only_cue_segments = 0
    parenthetical_only_cue_segments = 0
    html_tag_segments = 0
    html_entity_segments = 0

    for segment in segments:
        text = segment.get("text")
        start = segment.get("start")
        duration = segment.get("duration")

        if not isinstance(text, str) or not text.strip():
            empty_segments += 1
        else:
            cleaned_texts.append(text.strip())
            normalized_texts.append(
                re.sub(r"\s+", " ", text).strip().casefold()
            )
            leading_or_trailing_whitespace += int(text != text.strip())
            multiline_segments += int("\n" in text or "\r" in text)
            code_signal_count += len(PYTHON_CODE_SIGNAL.findall(text))
            contains_cr_segments += int("\r" in text)
            contains_tab_segments += int("\t" in text)
            contains_nbsp_segments += int("\u00a0" in text)
            contains_zero_width_segments += int(
                any(character in text for character in "\u200b\u200c\u200d\ufeff")
            )
            contains_replacement_character_segments += int("\ufffd" in text)
            non_nfc_segments += int(unicodedata.normalize("NFC", text) != text)
            multiple_ascii_space_segments += int("  " in text)
            line_with_edge_whitespace_segments += int(
                any(line != line.strip() for line in text.splitlines())
            )
            bracket_only_cue_segments += int(bool(BRACKET_ONLY_CUE.fullmatch(text)))
            parenthetical_only_cue_segments += int(
                bool(PARENTHETICAL_ONLY_CUE.fullmatch(text))
            )
            html_tag_segments += int(bool(HTML_TAG.search(text)))
            html_entity_segments += int(html.unescape(text) != text)

        if not isinstance(start, (int, float)) or isinstance(start, bool) or start < 0:
            invalid_start += 1
            continue
        if (
            not isinstance(duration, (int, float))
            or isinstance(duration, bool)
            or duration <= 0
        ):
            nonpositive_duration += 1
            continue

        end_second = start + duration
        maximum_end_second = max(maximum_end_second, end_second)
        if previous_start is not None and start < previous_start:
            out_of_order_segments += 1
        if previous_end is not None and start < previous_end:
            overlapping_segments += 1
        previous_start = start
        previous_end = end_second

    try:
        datetime.fromisoformat(payload["fetched_at"].replace("Z", "+00:00"))
        fetched_at_parseable = True
    except (AttributeError, TypeError, ValueError):
        fetched_at_parseable = False

    exact_adjacent_duplicates = 0
    normalized_adjacent_duplicates = 0
    adjacent_text_containment = 0
    for left, right, normalized_left, normalized_right in zip(
        cleaned_texts,
        cleaned_texts[1:],
        normalized_texts,
        normalized_texts[1:],
    ):
        exact_adjacent_duplicates += int(left == right)
        normalized_adjacent_duplicates += int(
            normalized_left == normalized_right and left != right
        )
        adjacent_text_containment += int(
            bool(
                normalized_left
                and normalized_right
                and normalized_left != normalized_right
                and (
                    normalized_left in normalized_right
                    or normalized_right in normalized_left
                )
            )
        )

    if empty_segments:
        failures.append(f"empty_segments={empty_segments}")
    if invalid_start:
        failures.append(f"invalid_start={invalid_start}")
    if nonpositive_duration:
        failures.append(f"nonpositive_duration={nonpositive_duration}")
    if out_of_order_segments:
        failures.append(f"out_of_order_segments={out_of_order_segments}")
    if not fetched_at_parseable:
        failures.append("fetched_at is not ISO-8601")

    profile = {
        "scope_version": SCOPE_VERSION,
        "playlist_position": manifest_row["playlist_position"],
        "video_id": payload["video_id"],
        "title": manifest_row["title"],
        "language_code": payload["language_code"],
        "language": payload["language"],
        "is_generated": payload["is_generated"],
        "fetched_at": payload["fetched_at"],
        "fetched_at_parseable": fetched_at_parseable,
        "segment_count": len(segments),
        "empty_segment_count": empty_segments,
        "leading_or_trailing_whitespace_segments": leading_or_trailing_whitespace,
        "multiline_segment_count": multiline_segments,
        "contains_cr_segment_count": contains_cr_segments,
        "contains_tab_segment_count": contains_tab_segments,
        "contains_nbsp_segment_count": contains_nbsp_segments,
        "contains_zero_width_segment_count": contains_zero_width_segments,
        "contains_replacement_character_segment_count": (
            contains_replacement_character_segments
        ),
        "non_nfc_segment_count": non_nfc_segments,
        "multiple_ascii_space_segment_count": multiple_ascii_space_segments,
        "line_with_edge_whitespace_segment_count": (
            line_with_edge_whitespace_segments
        ),
        "bracket_only_cue_segment_count": bracket_only_cue_segments,
        "parenthetical_only_cue_segment_count": parenthetical_only_cue_segments,
        "html_tag_segment_count": html_tag_segments,
        "html_entity_segment_count": html_entity_segments,
        "exact_adjacent_duplicate_count": exact_adjacent_duplicates,
        "normalized_adjacent_duplicate_count": normalized_adjacent_duplicates,
        "adjacent_text_containment_count": adjacent_text_containment,
        "invalid_start_count": invalid_start,
        "nonpositive_duration_count": nonpositive_duration,
        "out_of_order_segment_count": out_of_order_segments,
        "overlapping_segment_count": overlapping_segments,
        "transcript_length": len("\n".join(cleaned_texts)),
        "maximum_end_second": round(maximum_end_second, 3),
        "python_code_signal_count": code_signal_count,
        "validation_status": "passed" if not failures else "failed",
    }
    return profile, failures


def build_summary(
    payload_profiles: list[dict],
    schema_rows: list[dict],
    total_segments: int,
    unexpected_payload_fields: list[str],
    unexpected_segment_fields: list[str],
    failures: list[str],
) -> list[dict]:
    """Tạo các chỉ số tổng hợp dùng để review contract và cleaning policy."""

    segment_counts = [row["segment_count"] for row in payload_profiles]
    transcript_lengths = [row["transcript_length"] for row in payload_profiles]

    metrics = {
        "scope_version": SCOPE_VERSION,
        "target_payloads": len(payload_profiles),
        "unique_target_video_ids": len(
            {row["video_id"] for row in payload_profiles}
        ),
        "total_segments": total_segments,
        "payload_schema_fields": len(PAYLOAD_SCHEMA),
        "segment_schema_fields": len(SEGMENT_SCHEMA),
        "schema_fields_failed": sum(
            row["status"] == "failed" for row in schema_rows
        ),
        "unexpected_payload_fields": ",".join(unexpected_payload_fields),
        "unexpected_segment_fields": ",".join(unexpected_segment_fields),
        "language_codes": ",".join(
            sorted({row["language_code"] for row in payload_profiles})
        ),
        "language_names": " | ".join(
            sorted({row["language"] for row in payload_profiles})
        ),
        "generated_payloads": sum(
            bool(row["is_generated"]) for row in payload_profiles
        ),
        "manual_payloads": sum(
            not bool(row["is_generated"]) for row in payload_profiles
        ),
        "minimum_segment_count": min(segment_counts),
        "maximum_segment_count": max(segment_counts),
        "average_segment_count": round(sum(segment_counts) / len(segment_counts)),
        "minimum_transcript_length": min(transcript_lengths),
        "maximum_transcript_length": max(transcript_lengths),
        "average_transcript_length": round(
            sum(transcript_lengths) / len(transcript_lengths)
        ),
        "payloads_with_validation_failure": sum(
            row["validation_status"] == "failed" for row in payload_profiles
        ),
        "unparseable_fetched_at": sum(
            not row["fetched_at_parseable"] for row in payload_profiles
        ),
        "empty_segments": sum(
            row["empty_segment_count"] for row in payload_profiles
        ),
        "segments_with_edge_whitespace": sum(
            row["leading_or_trailing_whitespace_segments"]
            for row in payload_profiles
        ),
        "multiline_segments": sum(
            row["multiline_segment_count"] for row in payload_profiles
        ),
        "invalid_segment_starts": sum(
            row["invalid_start_count"] for row in payload_profiles
        ),
        "nonpositive_segment_durations": sum(
            row["nonpositive_duration_count"] for row in payload_profiles
        ),
        "out_of_order_segments": sum(
            row["out_of_order_segment_count"] for row in payload_profiles
        ),
        "overlapping_segment_pairs": sum(
            row["overlapping_segment_count"] for row in payload_profiles
        ),
        "validation_failures": len(failures),
        "validation_status": "passed" if not failures else "failed",
    }

    return [{"metric": key, "value": value} for key, value in metrics.items()]


def build_policy_evidence(payload_profiles: list[dict]) -> list[dict]:
    """Tạo aggregate evidence riêng cho quyết định Cleaning Policy v1."""

    metrics = {
        "scope_version": SCOPE_VERSION,
        "target_payloads": len(payload_profiles),
        "total_segments": sum(
            row["segment_count"] for row in payload_profiles
        ),
        "segments_with_lf_or_cr": sum(
            row["multiline_segment_count"] for row in payload_profiles
        ),
        "segments_with_cr": sum(
            row["contains_cr_segment_count"] for row in payload_profiles
        ),
        "segments_with_tab": sum(
            row["contains_tab_segment_count"] for row in payload_profiles
        ),
        "segments_with_nbsp": sum(
            row["contains_nbsp_segment_count"] for row in payload_profiles
        ),
        "segments_with_zero_width_character": sum(
            row["contains_zero_width_segment_count"] for row in payload_profiles
        ),
        "segments_with_replacement_character": sum(
            row["contains_replacement_character_segment_count"]
            for row in payload_profiles
        ),
        "non_nfc_segments": sum(
            row["non_nfc_segment_count"] for row in payload_profiles
        ),
        "segments_with_multiple_ascii_spaces": sum(
            row["multiple_ascii_space_segment_count"] for row in payload_profiles
        ),
        "segments_with_line_edge_whitespace": sum(
            row["line_with_edge_whitespace_segment_count"]
            for row in payload_profiles
        ),
        "bracket_only_cue_segments": sum(
            row["bracket_only_cue_segment_count"] for row in payload_profiles
        ),
        "parenthetical_only_cue_segments": sum(
            row["parenthetical_only_cue_segment_count"]
            for row in payload_profiles
        ),
        "html_tag_segments": sum(
            row["html_tag_segment_count"] for row in payload_profiles
        ),
        "html_entity_segments": sum(
            row["html_entity_segment_count"] for row in payload_profiles
        ),
        "exact_adjacent_duplicates": sum(
            row["exact_adjacent_duplicate_count"] for row in payload_profiles
        ),
        "normalized_adjacent_duplicates": sum(
            row["normalized_adjacent_duplicate_count"] for row in payload_profiles
        ),
        "adjacent_text_containment_pairs": sum(
            row["adjacent_text_containment_count"] for row in payload_profiles
        ),
        "overlapping_segment_pairs": sum(
            row["overlapping_segment_count"] for row in payload_profiles
        ),
    }
    return [{"metric": key, "value": value} for key, value in metrics.items()]


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    """Ghi CSV UTF-8 có BOM theo cách deterministic và atomic.

    Nếu report hiện có đã byte-identical thì không mở file để ghi. Cách này tránh
    lỗi file lock không cần thiết khi người dùng đang đọc một report không đổi.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(
        buffer,
        fieldnames=fieldnames,
        extrasaction="ignore",
    )
    writer.writeheader()
    writer.writerows(rows)
    output_bytes = buffer.getvalue().encode("utf-8-sig")

    if path.exists() and path.read_bytes() == output_bytes:
        return

    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    temporary_path.write_bytes(output_bytes)
    temporary_path.replace(path)


def main() -> None:
    """Chạy audit, ghi ba report và dừng với exit code khác 0 nếu schema lỗi."""

    manifest = load_manifest()
    manifest_by_id = {row["video_id"]: row for row in manifest}
    payloads = load_target_payloads(set(manifest_by_id))
    payloads_by_id = {payload["video_id"]: payload for payload in payloads}
    ordered_payloads = [payloads_by_id[row["video_id"]] for row in manifest]

    all_segments = [
        segment
        for payload in ordered_payloads
        for segment in payload.get("segments", [])
    ]
    payload_schema_rows, payload_schema_failures = field_profile(
        ordered_payloads, PAYLOAD_SCHEMA, "payload"
    )
    segment_schema_rows, segment_schema_failures = field_profile(
        all_segments, SEGMENT_SCHEMA, "segment"
    )
    schema_rows = payload_schema_rows + segment_schema_rows

    payload_profiles = []
    payload_failures = []
    for payload in ordered_payloads:
        profile, failures = profile_payload(
            manifest_by_id[payload["video_id"]], payload
        )
        payload_profiles.append(profile)
        payload_failures.extend(
            f"{payload['video_id']}: {failure}" for failure in failures
        )

    observed_payload_fields = {
        field_name for payload in ordered_payloads for field_name in payload
    }
    observed_segment_fields = {
        field_name for segment in all_segments for field_name in segment
    }
    unexpected_payload_fields = sorted(
        observed_payload_fields - set(PAYLOAD_SCHEMA)
    )
    unexpected_segment_fields = sorted(
        observed_segment_fields - set(SEGMENT_SCHEMA)
    )

    failures = (
        payload_schema_failures
        + segment_schema_failures
        + payload_failures
    )
    summary_rows = build_summary(
        payload_profiles,
        schema_rows,
        len(all_segments),
        unexpected_payload_fields,
        unexpected_segment_fields,
        failures,
    )
    policy_evidence_rows = build_policy_evidence(payload_profiles)
    existing_summary_metrics = {row["metric"] for row in summary_rows}
    summary_rows.extend(
        row
        for row in policy_evidence_rows
        if row["metric"] not in existing_summary_metrics
    )

    write_csv(SCHEMA_REPORT, list(schema_rows[0]), schema_rows)
    write_csv(PAYLOAD_REPORT, list(payload_profiles[0]), payload_profiles)
    write_csv(SUMMARY_REPORT, ["metric", "value"], summary_rows)

    print(f"Target payloads       : {len(payload_profiles)}")
    print(f"Total segments        : {len(all_segments)}")
    print(f"Schema fields failed  : {len(payload_schema_failures + segment_schema_failures)}")
    print(f"Payload failures      : {len(payload_failures)}")
    print(f"Validation status     : {'FAILED' if failures else 'PASSED'}")
    print(f"Schema report         : {SCHEMA_REPORT}")
    print(f"Payload report        : {PAYLOAD_REPORT}")
    print(f"Summary report        : {SUMMARY_REPORT}")

    if failures:
        raise RuntimeError("; ".join(failures))


if __name__ == "__main__":
    main()
