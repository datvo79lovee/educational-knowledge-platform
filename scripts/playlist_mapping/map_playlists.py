"""Recover public YouTube playlist membership for the transcript corpus.

The script calls only channel, playlist, and playlist-item endpoints. It does not
download video metadata or transcripts. Progress is checkpointed after every
playlist so an interrupted crawl can resume without starting from the beginning.
"""

import argparse
import csv
import json
import os
import sys
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_connection
from scripts.corpus_analysis.analyze_corpus import classify_domain, extract_course


DEFAULT_CHANNEL_ID = "UCEBb1b_L6zDS3xTUrIALZOw"
REPORTS_DIR = Path("reports/03_playlist_mapping")
CACHE_DIR = Path("data/bronze/playlist_mapping")
PLAYLIST_CACHE = CACHE_DIR / "playlists.json"
MATCH_CACHE = CACHE_DIR / "video_playlist_matches.jsonl"
COMPLETED_CACHE = CACHE_DIR / "completed_playlist_ids.txt"
CLASSIFICATION_REPORT = Path(
    "reports/02_corpus_analysis/transcript_classification.csv"
)


def create_youtube_client():
    """Build an authenticated YouTube Data API client from ``.env``."""

    load_dotenv()
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise RuntimeError("YOUTUBE_API_KEY is missing from the environment or .env")
    return build("youtube", "v3", developerKey=api_key, cache_discovery=False)


def fetch_target_videos() -> dict[str, str]:
    """Return the 290 PostgreSQL videos that currently have transcripts."""

    connection = get_connection()
    try:
        connection.set_session(readonly=True, autocommit=False)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT v.video_id, v.title
                FROM transcripts t
                JOIN videos v ON v.video_id = t.video_id
                ORDER BY v.video_id
                """
            )
            rows = cursor.fetchall()
        connection.rollback()
        return {video_id: title for video_id, title in rows}
    finally:
        connection.close()


def fetch_uploads_playlist_id(youtube, channel_id: str) -> str:
    """Find the uploads playlist so it can be excluded from course mapping."""

    response = youtube.channels().list(
        part="contentDetails",
        id=channel_id,
        maxResults=1,
    ).execute()
    items = response.get("items", [])
    if not items:
        raise RuntimeError(f"YouTube channel was not found: {channel_id}")
    return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]


def fetch_public_playlists(youtube, channel_id: str) -> list[dict]:
    """Fetch all public playlists owned by the channel with pagination."""

    playlists = []
    page_token = None

    while True:
        response = youtube.playlists().list(
            part="snippet,contentDetails",
            channelId=channel_id,
            maxResults=50,
            pageToken=page_token,
        ).execute()

        for item in response.get("items", []):
            snippet = item.get("snippet", {})
            playlists.append(
                {
                    "playlist_id": item["id"],
                    "title": snippet.get("title", ""),
                    "description": snippet.get("description", ""),
                    "published_at": snippet.get("publishedAt", ""),
                    "item_count": item.get("contentDetails", {}).get("itemCount", 0),
                }
            )

        page_token = response.get("nextPageToken")
        if not page_token:
            return playlists


def save_playlist_cache(playlists: list[dict]) -> None:
    """Cache playlist metadata so resume runs do not spend the same API quota."""

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with PLAYLIST_CACHE.open("w", encoding="utf-8") as file:
        json.dump(playlists, file, ensure_ascii=False, indent=2)


def load_or_fetch_playlists(youtube, channel_id: str, refresh: bool) -> list[dict]:
    if PLAYLIST_CACHE.exists() and not refresh:
        with PLAYLIST_CACHE.open("r", encoding="utf-8") as file:
            return json.load(file)

    playlists = fetch_public_playlists(youtube, channel_id)
    save_playlist_cache(playlists)
    return playlists


def load_completed_playlist_ids() -> set[str]:
    if not COMPLETED_CACHE.exists():
        return set()
    with COMPLETED_CACHE.open("r", encoding="utf-8") as file:
        return {line.strip() for line in file if line.strip()}


def mark_playlist_completed(playlist_id: str) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with COMPLETED_CACHE.open("a", encoding="utf-8") as file:
        file.write(f"{playlist_id}\n")


def append_matches(matches: list[dict]) -> None:
    if not matches:
        return
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with MATCH_CACHE.open("a", encoding="utf-8") as file:
        for match in matches:
            file.write(json.dumps(match, ensure_ascii=False))
            file.write("\n")


def fetch_playlist_matches(
    youtube,
    playlist: dict,
    target_video_ids: set[str],
) -> list[dict]:
    """Read one playlist and retain only items belonging to the corpus."""

    matches = []
    page_token = None

    while True:
        response = youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=playlist["playlist_id"],
            maxResults=50,
            pageToken=page_token,
        ).execute()

        for item in response.get("items", []):
            content_details = item.get("contentDetails", {})
            snippet = item.get("snippet", {})
            video_id = content_details.get("videoId") or snippet.get(
                "resourceId", {}
            ).get("videoId")
            if video_id not in target_video_ids:
                continue

            matches.append(
                {
                    "video_id": video_id,
                    "playlist_id": playlist["playlist_id"],
                    "playlist_title": playlist["title"],
                    "position": snippet.get("position", ""),
                    "item_published_at": content_details.get("videoPublishedAt", ""),
                }
            )

        page_token = response.get("nextPageToken")
        if not page_token:
            return matches


def crawl_playlists(
    youtube,
    playlists: list[dict],
    target_video_ids: set[str],
    uploads_playlist_id: str,
    max_playlists: int | None,
) -> None:
    """Crawl incomplete curated playlists and checkpoint each completed ID."""

    completed_ids = load_completed_playlist_ids()
    candidates = [
        playlist
        for playlist in playlists
        if playlist["playlist_id"] != uploads_playlist_id
        and playlist["playlist_id"] not in completed_ids
    ]
    if max_playlists is not None:
        candidates = candidates[:max_playlists]

    for index, playlist in enumerate(candidates, start=1):
        try:
            matches = fetch_playlist_matches(youtube, playlist, target_video_ids)
        except HttpError as error:
            # Do not checkpoint a failed playlist. The next run will retry it.
            raise RuntimeError(
                f"Playlist crawl failed for {playlist['playlist_id']} "
                f"({playlist['title']}): {error}"
            ) from error

        append_matches(matches)
        mark_playlist_completed(playlist["playlist_id"])
        print(
            f"Playlist {index}/{len(candidates)}: "
            f"{playlist['playlist_id']} matches={len(matches)}"
        )


def load_deduplicated_matches() -> list[dict]:
    """Deduplicate cache rows in case a process stopped before checkpointing."""

    if not MATCH_CACHE.exists():
        return []

    matches = {}
    with MATCH_CACHE.open("r", encoding="utf-8") as file:
        for line in file:
            record = json.loads(line)
            key = (record["video_id"], record["playlist_id"])
            matches[key] = record
    return sorted(matches.values(), key=lambda row: (row["video_id"], row["playlist_id"]))


def load_classification() -> dict[str, dict]:
    if not CLASSIFICATION_REPORT.exists():
        return {}
    with CLASSIFICATION_REPORT.open("r", encoding="utf-8-sig", newline="") as file:
        return {row["video_id"]: row for row in csv.DictReader(file)}


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_reports(
    playlists: list[dict],
    matches: list[dict],
    target_videos: dict[str, str],
    uploads_playlist_id: str,
) -> dict[str, int]:
    """Write playlist metadata, mappings, and one coverage row per corpus video."""

    curated_playlists = [
        playlist for playlist in playlists if playlist["playlist_id"] != uploads_playlist_id
    ]
    matches_by_video: dict[str, list[dict]] = {}
    matches_by_playlist = Counter()
    for match in matches:
        matches_by_video.setdefault(match["video_id"], []).append(match)
        matches_by_playlist[match["playlist_id"]] += 1

    classification = load_classification()
    coverage_rows = []
    for video_id, title in sorted(target_videos.items()):
        video_matches = matches_by_video.get(video_id, [])
        analysis = classification.get(video_id, {})
        playlist_course_codes = set()
        playlist_domains = set()

        for match in video_matches:
            code, course_name, _, _ = extract_course(match["playlist_title"], "")
            if code == "unresolved":
                continue
            playlist_course_codes.add(code)
            domain, _ = classify_domain(code, course_name, match["playlist_title"])
            if domain != "unresolved":
                playlist_domains.add(domain)

        # A playlist fallback is accepted only when every usable playlist agrees.
        # Conflicting playlist labels stay unresolved for manual review.
        playlist_course_code = (
            next(iter(playlist_course_codes))
            if len(playlist_course_codes) == 1
            else "unresolved"
        )
        playlist_domain = (
            next(iter(playlist_domains))
            if len(playlist_domains) == 1
            else "unresolved"
        )
        metadata_course_code = analysis.get("course_code", "unresolved")
        metadata_domain = analysis.get("domain", "unresolved")
        final_course_code = (
            metadata_course_code
            if metadata_course_code != "unresolved"
            else playlist_course_code
        )
        final_domain = (
            metadata_domain if metadata_domain != "unresolved" else playlist_domain
        )

        coverage_rows.append(
            {
                "video_id": video_id,
                "title": title,
                "playlist_count": len(video_matches),
                "playlist_ids": " | ".join(row["playlist_id"] for row in video_matches),
                "playlist_titles": " | ".join(
                    row["playlist_title"] for row in video_matches
                ),
                "metadata_course_code": metadata_course_code,
                "playlist_course_code": playlist_course_code,
                "final_course_code": final_course_code,
                "metadata_domain": metadata_domain,
                "playlist_domain": playlist_domain,
                "final_domain": final_domain,
            }
        )

    distribution_rows = [
        {
            "playlist_id": playlist["playlist_id"],
            "playlist_title": playlist["title"],
            "playlist_item_count": playlist["item_count"],
            "matched_transcript_videos": matches_by_playlist.get(
                playlist["playlist_id"], 0
            ),
        }
        for playlist in curated_playlists
        if matches_by_playlist.get(playlist["playlist_id"], 0) > 0
    ]
    distribution_rows.sort(
        key=lambda row: (-row["matched_transcript_videos"], row["playlist_title"])
    )

    write_csv(
        REPORTS_DIR / "playlists.csv",
        ["playlist_id", "title", "description", "published_at", "item_count"],
        curated_playlists,
    )
    write_csv(
        REPORTS_DIR / "video_playlist.csv",
        [
            "video_id",
            "playlist_id",
            "playlist_title",
            "position",
            "item_published_at",
        ],
        matches,
    )
    write_csv(
        REPORTS_DIR / "playlist_coverage.csv",
        [
            "video_id",
            "title",
            "playlist_count",
            "playlist_ids",
            "playlist_titles",
            "metadata_course_code",
            "playlist_course_code",
            "final_course_code",
            "metadata_domain",
            "playlist_domain",
            "final_domain",
        ],
        coverage_rows,
    )
    write_csv(
        REPORTS_DIR / "playlist_distribution.csv",
        [
            "playlist_id",
            "playlist_title",
            "playlist_item_count",
            "matched_transcript_videos",
        ],
        distribution_rows,
    )

    mapped_videos = sum(row["playlist_count"] > 0 for row in coverage_rows)
    multi_playlist_videos = sum(row["playlist_count"] > 1 for row in coverage_rows)
    return {
        "public_curated_playlists": len(curated_playlists),
        "mapping_rows": len(matches),
        "mapped_videos": mapped_videos,
        "unmapped_videos": len(target_videos) - mapped_videos,
        "multi_playlist_videos": multi_playlist_videos,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Map transcript videos to public channel playlists."
    )
    parser.add_argument("--channel-id", default=DEFAULT_CHANNEL_ID)
    parser.add_argument(
        "--refresh-playlists",
        action="store_true",
        help="Ignore cached playlist metadata and fetch the list again.",
    )
    parser.add_argument(
        "--max-playlists",
        type=int,
        default=None,
        help="Process at most N incomplete playlists for a controlled test run.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    youtube = create_youtube_client()
    target_videos = fetch_target_videos()
    if len(target_videos) != 290:
        raise RuntimeError(
            f"Expected 290 transcript videos, found {len(target_videos)} in PostgreSQL"
        )

    uploads_playlist_id = fetch_uploads_playlist_id(youtube, args.channel_id)
    playlists = load_or_fetch_playlists(
        youtube, args.channel_id, args.refresh_playlists
    )
    crawl_playlists(
        youtube,
        playlists,
        set(target_videos),
        uploads_playlist_id,
        args.max_playlists,
    )

    matches = load_deduplicated_matches()
    summary = write_reports(
        playlists, matches, target_videos, uploads_playlist_id
    )

    print(f"Public curated playlists : {summary['public_curated_playlists']}")
    print(f"Video-playlist rows       : {summary['mapping_rows']}")
    print(f"Mapped transcript videos : {summary['mapped_videos']}")
    print(f"Unmapped videos          : {summary['unmapped_videos']}")
    print(f"Videos in >1 playlist    : {summary['multi_playlist_videos']}")


if __name__ == "__main__":
    main()
