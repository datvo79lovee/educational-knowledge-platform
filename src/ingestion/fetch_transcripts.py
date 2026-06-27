from youtube_transcript_api import YouTubeTranscriptApi


def fetch_transcript(video_id, raise_errors=False):
    """
    Fetch transcript for a single video.

    Parameters
    ----------
    video_id : str
    raise_errors : bool

    Returns
    -------
    dict | None
    """

    try:

        transcript = YouTubeTranscriptApi().fetch(video_id)

        record = {
            "video_id": video_id,
            "language": transcript.language,
            "language_code": transcript.language_code,
            "is_generated": transcript.is_generated,
            "segments": []
        }

        for segment in transcript:

            record["segments"].append(
                {
                    "text": segment.text,
                    "start": segment.start,
                    "duration": segment.duration
                }
            )

        return record

    except Exception as e:

        if raise_errors:
            raise

        print(
            f"[ERROR] Failed to fetch transcript "
            f"for {video_id}: {e}"
        )

        return None


def fetch_transcripts(video_ids):
    """
    Fetch transcripts for multiple videos.

    Parameters
    ----------
    video_ids : list[str]

    Returns
    -------
    list[dict]
    """

    transcripts = []

    failed_videos = []

    success_count = 0
    failed_count = 0

    total_videos = len(video_ids)

    for index, video_id in enumerate(
        video_ids,
        start=1
    ):

        print(
            f"[INFO] Processing "
            f"{index}/{total_videos}: "
            f"{video_id}"
        )

        try:

            record = fetch_transcript(video_id)

            if record:

                transcripts.append(record)

                success_count += 1

            else:

                failed_count += 1

                failed_videos.append(
                    {
                        "video_id": video_id,
                        "error": "Transcript fetch failed"
                    }
                )

        except Exception as e:

            failed_count += 1

            failed_videos.append(
                {
                    "video_id": video_id,
                    "error": str(e)
                }
            )

    print("\n===== TRANSCRIPT COLLECTION REPORT =====")

    print(f"Videos Tested : {total_videos}")
    print(f"Success       : {success_count}")
    print(f"Failed        : {failed_count}")

    if total_videos > 0:

        success_rate = (
            success_count
            / total_videos
            * 100
        )

        print(
            f"Success Rate  : "
            f"{success_rate:.2f}%"
        )

    if failed_videos:

        print("\n===== FAILED VIDEOS =====")

        for item in failed_videos:

            print(
                f"{item['video_id']} "
                f"-> {item['error']}"
            )

    return transcripts
# if __name__ == "__main__":

#     video_id = "oz1iDMr5INo"

#     transcript_record = fetch_transcript(video_id)

#     print(transcript_record["video_id"])
#     print(transcript_record["language"])
#     print(len(transcript_record["segments"]))
#     print(type(transcript_record))
#     print(transcript_record["segments"][-1])
#     print(transcript_record.keys())
