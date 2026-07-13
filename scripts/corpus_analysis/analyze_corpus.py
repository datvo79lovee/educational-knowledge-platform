"""Classify the current transcript corpus from existing metadata.

This is a read-only, evidence-preserving analysis. Heuristic results are written
to CSV reports and are not persisted back to PostgreSQL.
"""

import csv
import re
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_connection


REPORTS_DIR = Path("reports/02_corpus_analysis")

COURSE_CODE_PATTERN = re.compile(
    r"\b(?:MIT\s+)?(RES[.-]\d+(?:[-.][A-Z]?\d+)*|"
    r"[A-Z]{2,5}[.-]\d+(?:[-.]\d+)*(?:[A-Z]+)?|"
    r"\d+[A-Z]*(?:\.\d+)+(?:[A-Z]+)?)\b",
    re.IGNORECASE,
)
TERM_PATTERN = re.compile(
    r",?\s+(?:Fall|Spring|Summer|Winter|IAP)\s+\d{4}\b", re.IGNORECASE
)

DOMAIN_KEYWORDS = {
    "computer_science_ai_data": (
        "algorithm", "computer science", "programming", "python", "software",
        "machine learning", "deep learning", "artificial intelligence", "data science",
        "computation", "computational", "optimization", "database", "coding",
    ),
    "mathematics_statistics": (
        "calculus", "linear algebra", "differential equation", "probability",
        "statistics", "mathematics", "mathematical", "geometry", "algebra",
    ),
    "physics": (
        "physics", "quantum", "mechanics", "electromagnet", "relativity",
        "optics", "laser", "thermodynamics",
    ),
    "biology_medicine_neuroscience": (
        "biology", "biological", "genomics", "genetics", "neuroscience", "brain",
        "medical", "medicine", "health", "sensory", "autism", "biochemistry",
    ),
    "engineering": (
        "engineering", "manufacturing", "aeronaut", "aircraft", "control system",
        "materials", "circuits", "electronics", "robot", "energy", "chemical",
    ),
    "economics_business_management": (
        "economics", "economic", "finance", "business", "management", "marketing",
        "entrepreneur", "contract", "accounting",
    ),
    "humanities_social_science": (
        "history", "philosophy", "ethics", "political", "politics", "literature",
        "language", "community", "anthropology", "sociology", "psychology", "music",
    ),
    "architecture_urban_studies": (
        "architecture", "urban", "planning", "design studio", "city", "cities",
    ),
    "education_communication_media": (
        "education", "teaching", "learning", "communication", "media", "video game",
    ),
}

DEPARTMENT_DOMAINS = {
    "6": "computer_science_ai_data",
    "18": "mathematics_statistics",
    "8": "physics",
    "7": "biology_medicine_neuroscience",
    "9": "biology_medicine_neuroscience",
    "20": "biology_medicine_neuroscience",
    "2": "engineering",
    "3": "engineering",
    "10": "engineering",
    "16": "engineering",
    "22": "engineering",
    "14": "economics_business_management",
    "15": "economics_business_management",
    "11": "architecture_urban_studies",
    "4": "architecture_urban_studies",
    "17": "humanities_social_science",
    "21": "humanities_social_science",
    "24": "humanities_social_science",
    "CMS": "education_communication_media",
}


def normalize_space(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_course_code(value: str) -> str:
    return value.upper().replace("-", ".", 1) if value.upper().startswith("RES-") else value.upper()


def extract_course(title: str, description: str) -> tuple[str, str, str, str]:
    sources = (("title", normalize_space(title)), ("description", normalize_space(description)))

    for source_name, text in sources:
        for match in COURSE_CODE_PATTERN.finditer(text):
            code = normalize_course_code(match.group(1))
            # Reject common decimal-like values that are not presented in MIT context.
            match_text = match.group(0).upper()
            has_mit_evidence = match_text.startswith("MIT ")
            if not has_mit_evidence:
                continue

            remainder = text[match.end():]
            remainder = remainder.lstrip(" |:-–—")
            term_match = TERM_PATTERN.search(remainder)
            if term_match:
                course_name = remainder[:term_match.start()].strip(" ,|:-–—")
            else:
                course_name = remainder.split(" View the complete course", 1)[0]
                course_name = course_name[:160].strip(" ,|:-–—")

            if not course_name or course_name.lower().startswith(("lec ", "lecture ")):
                course_name = ""

            confidence = "high" if has_mit_evidence else "medium"
            evidence = f"{source_name}:{match.group(0)}"
            return code, course_name, confidence, evidence

    return "unresolved", "unresolved", "unresolved", "no_course_code_pattern"


def classify_domain(course_code: str, course_name: str, title: str) -> tuple[str, str]:
    if course_code != "unresolved":
        department = re.split(r"[.]", course_code, maxsplit=1)[0]
        if department in DEPARTMENT_DOMAINS:
            return DEPARTMENT_DOMAINS[department], f"department:{department}"

    text = normalize_space(f"{course_name} {title}").lower()
    scores = {
        domain: sum(1 for keyword in keywords if keyword in text)
        for domain, keywords in DOMAIN_KEYWORDS.items()
    }
    best_score = max(scores.values(), default=0)
    if best_score == 0:
        return "unresolved", "no_domain_evidence"

    winners = sorted(domain for domain, score in scores.items() if score == best_score)
    if len(winners) > 1:
        return "unresolved", f"domain_tie:{'|'.join(winners)}"
    return winners[0], f"keyword_score:{best_score}"


def classify_short_transcript(length: int, duration: int | None) -> tuple[str, float | None]:
    if duration in (None, 0):
        return ("manual_review_missing_duration" if length < 5000 else "not_short"), None

    characters_per_second = length / duration
    if length >= 5000:
        return "not_short", round(characters_per_second, 3)
    if duration <= 600 and characters_per_second >= 2:
        return "likely_valid_short_video", round(characters_per_second, 3)
    if duration > 600 and characters_per_second < 2:
        return "possible_incomplete", round(characters_per_second, 3)
    return "manual_review", round(characters_per_second, 3)


def fetch_rows() -> list[tuple]:
    connection = get_connection()
    try:
        connection.set_session(readonly=True, autocommit=False)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    v.video_id,
                    v.title,
                    v.description,
                    v.publish_date,
                    v.duration_seconds,
                    LENGTH(t.raw_text) AS transcript_length
                FROM transcripts t
                JOIN videos v ON v.video_id = t.video_id
                ORDER BY v.video_id
                """
            )
            rows = cursor.fetchall()
        connection.rollback()
        return rows
    finally:
        connection.close()


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    output_rows = []

    for video_id, title, description, publish_date, duration, length in fetch_rows():
        course_code, course_name, course_confidence, course_evidence = extract_course(
            title, description or ""
        )
        domain, domain_evidence = classify_domain(course_code, course_name, title)
        short_status, characters_per_second = classify_short_transcript(length, duration)

        output_rows.append(
            {
                "video_id": video_id,
                "title": title,
                "publish_date": publish_date,
                "duration_seconds": duration,
                "transcript_length": length,
                "course_code": course_code,
                "course_name": course_name,
                "course_confidence": course_confidence,
                "course_evidence": course_evidence,
                "domain": domain,
                "domain_evidence": domain_evidence,
                "short_transcript_status": short_status,
                "characters_per_second": characters_per_second,
            }
        )

    rows_by_course = {}
    for row in output_rows:
        rows_by_course.setdefault(row["course_code"], []).append(row)

    course_distribution = []
    for code, course_rows in rows_by_course.items():
        names = Counter(
            row["course_name"] for row in course_rows if row["course_name"] != "unresolved"
        )
        representative_name = names.most_common(1)[0][0] if names else "unresolved"
        confidences = {row["course_confidence"] for row in course_rows}
        confidence = "high" if "high" in confidences else next(iter(confidences))
        course_distribution.append(
            {
                "course_code": code,
                "course_name": representative_name,
                "course_confidence": confidence,
                "transcript_count": len(course_rows),
            }
        )
    course_distribution.sort(key=lambda row: (-row["transcript_count"], row["course_code"]))

    domain_counts = Counter(row["domain"] for row in output_rows)
    transcript_distribution = [
        {
            "domain": domain,
            "transcript_count": count,
            "share_percent": round(count / len(output_rows) * 100, 2),
        }
        for domain, count in sorted(domain_counts.items(), key=lambda item: (-item[1], item[0]))
    ]

    short_rows = [row for row in output_rows if row["transcript_length"] < 5000]

    fields = list(output_rows[0].keys())
    write_csv(REPORTS_DIR / "transcript_classification.csv", fields, output_rows)
    write_csv(
        REPORTS_DIR / "course_distribution.csv",
        ["course_code", "course_name", "course_confidence", "transcript_count"],
        course_distribution,
    )
    write_csv(
        REPORTS_DIR / "transcript_distribution.csv",
        ["domain", "transcript_count", "share_percent"],
        transcript_distribution,
    )
    write_csv(REPORTS_DIR / "short_transcript_review.csv", fields, short_rows)

    unresolved_courses = sum(row["course_code"] == "unresolved" for row in output_rows)
    unresolved_domains = sum(row["domain"] == "unresolved" for row in output_rows)
    short_status_counts = Counter(row["short_transcript_status"] for row in short_rows)

    print(f"Transcripts        : {len(output_rows)}")
    print(f"Resolved courses   : {len(output_rows) - unresolved_courses}")
    print(f"Unresolved courses : {unresolved_courses}")
    print(f"Unresolved domains : {unresolved_domains}")
    print(f"Course groups      : {len(course_distribution)}")
    print(f"Short transcripts  : {len(short_rows)}")
    for status, count in sorted(short_status_counts.items()):
        print(f"Short {status:<28}: {count}")
    for domain, count in sorted(domain_counts.items(), key=lambda item: (-item[1], item[0])):
        print(f"Domain {domain:<35}: {count}")


if __name__ == "__main__":
    main()
