"""Promote configuration đã human approve thành canonical MIT 6.0001 Gold full.

Luồng chính của file:
1. Đọc decision CSV và yêu cầu đúng một configuration được chọn.
2. Khóa quyết định bằng SHA-256 của workbook re-audited.
3. Đối chiếu candidate với full validation và cross-process report đã có.
4. Kiểm lại từng Gold record từ Silver gốc.
5. Chép nguyên bytes candidate sang canonical output và ghi manifest/report.

File này không chạy lại thuật toán chunking. Mục tiêu là promotion một candidate
đã được build, đánh giá và human approve mà không làm thay đổi nội dung của nó.
"""

import argparse
import csv
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[2]
# Các path tương đối bên dưới luôn được đọc/ghi khi process chạy tại PROJECT_ROOT.
# Cross-process verifier cũng đặt cwd như vậy để kết quả không phụ thuộc shell gọi.
DECISION_FILE = Path("evaluation/review/chunking/mit_60001_chunking_configuration_decision_2026-08-12.csv")
FULL_VALIDATION_REPORT = Path("reports/08_chunking/full_chunk_validation.csv")
FULL_CROSS_PROCESS_REPORT = Path("reports/08_chunking/full_chunk_cross_process_validation.csv")
EXPERIMENT_ROOT = Path("data/gold/mit_60001/experiments")
CANONICAL_OUTPUT = Path("data/gold/mit_60001/chunks.jsonl")
SILVER_FILE = Path("data/silver/mit_60001/transcripts_clean.jsonl")
SCHEMA_FILE = Path("schemas/gold_chunk_v1.schema.json")
MANIFEST_FILE = Path("reports/08_chunking/canonical_gold_manifest.json")
VALIDATION_REPORT = Path("reports/08_chunking/canonical_gold_validation.csv")


def sha256_bytes(content: bytes) -> str:
    """Tính SHA-256 của bytes để khóa nội dung chính xác, kể cả encoding/newline."""

    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    """Đọc toàn bộ file dưới dạng bytes rồi tính SHA-256."""

    return sha256_bytes(path.read_bytes())


def canonical_bytes(value: dict) -> bytes:
    """Serialize object theo đúng quy tắc canonical của Gold content hash."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def write_atomic(path: Path, content: bytes) -> None:
    """Ghi qua file `.tmp`, chỉ replace đích sau khi bytes đã ghi hoàn chỉnh."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_bytes(content)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def load_jsonl(path: Path) -> list[dict]:
    """Parse các dòng JSON không rỗng thành list record."""

    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_csv(path: Path) -> list[dict]:
    """Đọc CSV có thể có UTF-8 BOM thành list dictionary."""

    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def serialize_csv(rows: list[dict]) -> bytes:
    """Serialize report CSV ổn định với header lấy từ thứ tự key của dòng đầu."""

    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")


def end_second(segment: dict) -> float:
    """Tính thời điểm kết thúc bằng Decimal, tránh artifact cộng float nhị phân."""

    return float(
        Decimal(str(segment["start_second"]))
        + Decimal(str(segment["duration_second"]))
    )


def selected_decision() -> tuple[dict, str]:
    """Lấy duy nhất winner và xác minh decision vẫn trỏ đúng workbook re-audited.

    Hash workbook ngăn trường hợp nội dung human review bị sửa sau khi decision CSV
    đã được tạo. Hàm trả cả selected row và hash của chính decision artifact để đưa
    vào canonical manifest.
    """

    rows = load_csv(DECISION_FILE)
    selected = [
        row
        for row in rows
        if row["selected"].lower() == "true" and row["decision_status"] == "selected"
    ]
    if len(rows) != 3 or len(selected) != 1:
        raise ValueError("Decision artifact must contain three configurations and one selected row")
    decision = selected[0]
    review_path = Path(decision["review_artifact"])
    if sha256_file(review_path) != decision["review_artifact_sha256"]:
        raise ValueError("Reaudited workbook hash differs from decision artifact")
    return decision, sha256_file(DECISION_FILE)


def validated_candidate(decision: dict) -> tuple[Path, bytes, dict]:
    """Nạp candidate được chọn sau khi xác minh ba nguồn hash độc lập.

    Candidate chỉ hợp lệ để promotion nếu:
    - có dòng `passed` trong full validation report;
    - hai lần full build có cùng hash trong cross-process report;
    - bytes hiện có trên disk vẫn cho đúng hash đã báo cáo.
    """

    config_id = decision["chunking_config_id"]
    validation_rows = {
        row["chunking_config_id"]: row for row in load_csv(FULL_VALIDATION_REPORT)
    }
    cross_rows = {
        row["chunking_config_id"]: row for row in load_csv(FULL_CROSS_PROCESS_REPORT)
    }
    if config_id not in validation_rows or config_id not in cross_rows:
        raise ValueError(f"Selected configuration is absent from full validation: {config_id}")
    validation = validation_rows[config_id]
    cross = cross_rows[config_id]
    if validation["validation_status"] != "passed":
        raise ValueError("Selected candidate did not pass full validation")
    if cross["hashes_match"] != "True" or cross["cross_process_deterministic"] != "True":
        raise ValueError("Selected candidate did not pass cross-process determinism")
    candidate_path = EXPERIMENT_ROOT / config_id / "chunks.jsonl"
    candidate = candidate_path.read_bytes()
    candidate_hash = sha256_bytes(candidate)
    if candidate_hash != validation["output_sha256"]:
        raise ValueError("Selected candidate hash differs from full validation report")
    if candidate_hash != cross["run_1_sha256"] or candidate_hash != cross["run_2_sha256"]:
        raise ValueError("Selected candidate hash differs from cross-process report")
    return candidate_path, candidate, validation


def validate_records(records: list[dict], config_id: str) -> dict:
    """Kiểm lại canonical candidate trực tiếp với schema và Silver source.

    Validation có hai tầng:
    - từng record: schema, config, metadata, source range, text, timing, lineage/hash;
    - toàn dataset: unique ID, chunk index liên tục và full Silver segment coverage.

    Hàm không tin report cũ một cách tuyệt đối; nó tái dựng expected values từ
    `transcripts_clean.jsonl` để phát hiện candidate bị thay đổi sau full build.
    """

    schema = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    silver_records = load_jsonl(SILVER_FILE)
    silver_by_video = {record["video_id"]: record for record in silver_records}
    expected_coverage = {
        (record["video_id"], segment["segment_index"])
        for record in silver_records
        for segment in record["segments"]
    }
    actual_coverage = set()
    errors = []
    schema_error_count = 0
    config_mismatch_count = 0

    # Kiểm từng chunk bằng chính Silver range mà chunk khai báo.
    for record in records:
        record_schema_errors = list(validator.iter_errors(record))
        schema_error_count += len(record_schema_errors)
        errors.extend(error.message for error in record_schema_errors)
        if record.get("chunking_config_id") != config_id:
            config_mismatch_count += 1
            errors.append(f"configuration mismatch: {record.get('chunk_id')}")
            continue
        silver = silver_by_video.get(record["video_id"])
        if silver is None:
            errors.append(f"video missing from Silver: {record['video_id']}")
            continue
        start = record["source_segment_start_index"]
        end = record["source_segment_end_index"]
        if start < 0 or end < start or end >= len(silver["segments"]):
            errors.append(f"invalid source range: {record['chunk_id']}")
            continue
        source = silver["segments"][start : end + 1]
        expected_text = "\n".join(segment["text"] for segment in source)
        expected_end = end_second(source[-1])
        # Payload này phải giống chính xác payload builder dùng để tạo content_sha256.
        expected_hash_input = {
            "video_id": record["video_id"],
            "chunking_config_id": config_id,
            "source_segment_start_index": start,
            "source_segment_end_index": end,
            "chunk_text": expected_text,
            "start_second": source[0]["start_second"],
            "end_second": expected_end,
        }
        expected_metadata = {
            "playlist_id": silver["playlist_id"],
            "playlist_position": silver["playlist_position"],
            "title": silver["title"],
        }
        if any(record[field] != value for field, value in expected_metadata.items()):
            errors.append(f"Silver metadata mismatch: {record['chunk_id']}")
        if record["source_segment_count"] != len(source):
            errors.append(f"source segment count mismatch: {record['chunk_id']}")
        if record["chunk_text"] != expected_text or record["chunk_length"] != len(expected_text):
            errors.append(f"text/length mismatch: {record['chunk_id']}")
        if record["start_second"] != source[0]["start_second"] or record["end_second"] != expected_end:
            errors.append(f"timing mismatch: {record['chunk_id']}")
        if record["lineage"] != {
            "silver_file": str(SILVER_FILE).replace("\\", "/"),
            "silver_content_sha256": silver["content_sha256"],
        }:
            errors.append(f"lineage mismatch: {record['chunk_id']}")
        if record["content_sha256"] != sha256_bytes(canonical_bytes(expected_hash_input)):
            errors.append(f"content hash mismatch: {record['chunk_id']}")
        # Overlap được phép nên dùng set; yêu cầu là mọi segment xuất hiện ít nhất một lần.
        actual_coverage.update((record["video_id"], index) for index in range(start, end + 1))

    # Kiểm các invariant ở cấp toàn dataset sau khi tất cả record đã được đọc.
    duplicate_chunk_id_count = len(records) - len({record["chunk_id"] for record in records})
    if duplicate_chunk_id_count:
        errors.append("duplicate chunk IDs")
    for video_id in silver_by_video:
        video_chunks = sorted(
            [record for record in records if record["video_id"] == video_id],
            key=lambda record: record["chunk_index"],
        )
        if [record["chunk_index"] for record in video_chunks] != list(range(len(video_chunks))):
            errors.append(f"non-contiguous chunk index: {video_id}")
        if any(
            record["chunk_id"] != f"{video_id}:{config_id}:{record['chunk_index']}"
            for record in video_chunks
        ):
            errors.append(f"chunk ID format mismatch: {video_id}")

    coverage_missing_count = len(expected_coverage - actual_coverage)
    coverage_extra_count = len(actual_coverage - expected_coverage)
    if coverage_missing_count or coverage_extra_count:
        errors.append("source segment coverage mismatch")
    if errors:
        raise RuntimeError(f"Canonical Gold validation failed ({len(errors)} errors): {errors[:5]}")
    return {
        "total_chunks": len(records),
        "video_count": len({record["video_id"] for record in records}),
        "silver_video_count": len(silver_records),
        "silver_segment_count": len(expected_coverage),
        "source_segment_coverage": actual_coverage == expected_coverage,
        "coverage_missing_count": coverage_missing_count,
        "coverage_extra_count": coverage_extra_count,
        "duplicate_chunk_id_count": duplicate_chunk_id_count,
        "schema_error_count": schema_error_count,
        "config_mismatch_count": config_mismatch_count,
        "validation_error_count": 0,
    }


def main() -> None:
    """Điều phối promotion và sinh hai artifact audit có thể tái tạo."""

    parser = argparse.ArgumentParser(description="Promote selected MIT 6.0001 chunk configuration.")
    parser.parse_args()

    decision, decision_hash = selected_decision()
    config_id = decision["chunking_config_id"]
    candidate_path, candidate, full_validation = validated_candidate(decision)
    records = [json.loads(line) for line in candidate.decode("utf-8").splitlines() if line.strip()]
    validation = validate_records(records, config_id)
    if validation["total_chunks"] != int(full_validation["total_chunks"]):
        raise ValueError("Canonical record count differs from full validation report")

    # Promotion nguyên bytes thay vì parse rồi serialize lại. Nhờ đó canonical file
    # phải có cùng SHA-256 với candidate đã được retrieval/human review.
    write_atomic(CANONICAL_OUTPUT, candidate)
    canonical_hash = sha256_file(CANONICAL_OUTPUT)
    candidate_hash = sha256_bytes(candidate)
    if canonical_hash != candidate_hash or CANONICAL_OUTPUT.read_bytes() != candidate:
        raise RuntimeError("Canonical output is not byte-identical to selected candidate")

    # Manifest giữ lineage đầy đủ từ human decision -> candidate -> canonical output.
    manifest = {
        "schema_version": "canonical_gold_manifest_v1",
        "scope_version": "mit_60001_fall_2016_v1",
        "decision_date": decision["decision_date"],
        "decision_artifact": str(DECISION_FILE).replace("\\", "/"),
        "decision_artifact_sha256": decision_hash,
        "review_artifact": decision["review_artifact"],
        "review_artifact_sha256": decision["review_artifact_sha256"],
        "selected_chunking_config_id": config_id,
        "source_candidate": str(candidate_path).replace("\\", "/"),
        "source_candidate_sha256": candidate_hash,
        "canonical_output": str(CANONICAL_OUTPUT).replace("\\", "/"),
        "canonical_output_sha256": canonical_hash,
        "canonical_byte_identical_to_candidate": True,
        "silver_file": str(SILVER_FILE).replace("\\", "/"),
        "silver_sha256": sha256_file(SILVER_FILE),
        "gold_schema": str(SCHEMA_FILE).replace("\\", "/"),
        "gold_schema_sha256": sha256_file(SCHEMA_FILE),
        **validation,
        "validation_status": "passed",
    }
    # CSV là bản validation phẳng, thuận tiện đọc trong CI hoặc spreadsheet.
    report_row = {
        "selected_chunking_config_id": config_id,
        "decision_artifact_sha256": decision_hash,
        "review_artifact_sha256": decision["review_artifact_sha256"],
        "source_candidate_sha256": candidate_hash,
        "canonical_output_sha256": canonical_hash,
        "canonical_byte_identical_to_candidate": True,
        **validation,
        "full_candidate_cross_process_deterministic": True,
        "validation_status": "passed",
    }
    write_atomic(
        MANIFEST_FILE,
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n",
    )
    write_atomic(VALIDATION_REPORT, serialize_csv([report_row]))
    print(json.dumps({
        "selected_chunking_config_id": config_id,
        "canonical_output": str(CANONICAL_OUTPUT).replace("\\", "/"),
        "canonical_output_sha256": canonical_hash,
        **validation,
        "validation_status": "passed",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
