"""Đề xuất source candidate cho evaluation draft, không tự tạo ground truth."""

import argparse
import csv
import io
import json
import re
import sys
from decimal import Decimal
from pathlib import Path

from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_DRAFT_FILE = Path("evaluation/drafts/mit_60001_question_drafts_batch_01.csv")
SILVER_FILE = Path("data/silver/mit_60001/transcripts_clean.jsonl")
DEFAULT_REPORT_FILE = Path("evaluation/review/batch_01/candidates/batch_01_source_candidates_with_transcript.csv")
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
WINDOW_TOKEN_MAX = 120
TOP_K = 5


def derived_text(segments: list[dict]) -> str:
    """Tạo text chỉ cho embedding; không ghi text này vào report."""

    return re.sub(r"\s+", " ", "\n".join(segment["text"] for segment in segments)).strip()


def end_second(segment: dict) -> float:
    """Tính timestamp dẫn xuất bằng Decimal để tránh float artifact."""

    return float(Decimal(str(segment["start_second"])) + Decimal(str(segment["duration_second"])))


def build_windows(record: dict, tokenizer) -> list[dict]:
    """Gom whole Silver segment thành window tối đa 120 word pieces."""

    segments, windows, start, index = record["segments"], [], 0, 0
    while index < len(segments):
        candidate = segments[start : index + 1]
        tokens = len(tokenizer.encode(derived_text(candidate), add_special_tokens=False, verbose=False))
        if index > start and tokens > WINDOW_TOKEN_MAX:
            source = segments[start:index]
            windows.append({"video_id": record["video_id"], "title": record["title"], "start_index": start, "end_index": index - 1, "start_second": source[0]["start_second"], "end_second": end_second(source[-1]), "start_transcript_text": source[0]["text"], "end_transcript_text": source[-1]["text"], "transcript_excerpt": "\n".join(segment["text"] for segment in source), "embedding_text": derived_text(source)})
            start = index
        else:
            index += 1
    source = segments[start:]
    windows.append({"video_id": record["video_id"], "title": record["title"], "start_index": start, "end_index": len(segments) - 1, "start_second": source[0]["start_second"], "end_second": end_second(source[-1]), "start_transcript_text": source[0]["text"], "end_transcript_text": source[-1]["text"], "transcript_excerpt": "\n".join(segment["text"] for segment in source), "embedding_text": derived_text(source)})
    return windows


def write_atomic(path: Path, content: bytes) -> None:
    """Ghi report qua temporary file rồi replace khi hoàn chỉnh."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_bytes(content)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    """Rank source candidates cho answerable draft và ghi metadata review-only."""

    parser = argparse.ArgumentParser(description="Locate review-only source candidates for evaluation drafts.")
    parser.add_argument(
        "--draft-file",
        type=Path,
        default=DEFAULT_DRAFT_FILE,
        help="CSV draft input; defaults to the existing Batch 01 draft file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_REPORT_FILE,
        help="CSV output path; use a new filename when an existing review file is open.",
    )
    args = parser.parse_args()
    drafts = list(csv.DictReader(args.draft_file.open(encoding="utf-8-sig", newline="")))
    silver_records = [json.loads(line) for line in SILVER_FILE.read_text(encoding="utf-8").splitlines()]
    model = SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION, local_files_only=True)
    windows = [window for record in silver_records for window in build_windows(record, model.tokenizer)]
    embeddings = model.encode([window["embedding_text"] for window in windows], normalize_embeddings=True)
    rows = []
    for draft in drafts:
        if draft["answerable"] != "True":
            rows.append({"question_id": draft["question_id"], "candidate_rank": "", "video_id": "", "title": "", "source_segment_start_index": "", "source_segment_end_index": "", "start_second": "", "end_second": "", "start_transcript_text": "", "end_transcript_text": "", "transcript_excerpt": "", "cosine_score": "", "candidate_status": "not_applicable_out_of_scope", "review_instruction": "Do not attach corpus evidence."})
            continue
        scores = embeddings @ model.encode([draft["question"]], normalize_embeddings=True)[0]
        ranked = sorted(range(len(windows)), key=lambda index: float(scores[index]), reverse=True)[:TOP_K]
        for rank, index in enumerate(ranked, start=1):
            window = windows[index]
            rows.append({"question_id": draft["question_id"], "candidate_rank": rank, "video_id": window["video_id"], "title": window["title"], "source_segment_start_index": window["start_index"], "source_segment_end_index": window["end_index"], "start_second": window["start_second"], "end_second": window["end_second"], "start_transcript_text": window["start_transcript_text"], "end_transcript_text": window["end_transcript_text"], "transcript_excerpt": window["transcript_excerpt"], "cosine_score": round(float(scores[index]), 6), "candidate_status": "candidate_requires_human_source_review", "review_instruction": "Read source before accepting any video/time range."})
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    write_atomic(args.output, buffer.getvalue().encode("utf-8-sig"))
    print(f"Draft questions: {len(drafts)}")
    print(f"Source windows: {len(windows)}")
    print(f"Candidate rows: {len(rows)}")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
