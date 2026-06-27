import json
import os

def append_jsonl(record, output_file):

    output_dir = os.path.dirname(
        os.fspath(output_file)
    )

    if output_dir:
        os.makedirs(
            output_dir,
            exist_ok=True
        )

    with open(
        output_file,
        "a",
        encoding="utf-8"
    ) as f:

        json.dump(
            record,
            f,
            ensure_ascii=False
        )

        f.write("\n")
def load_processed_video_ids(
    file_path
):
    """
    Load processed video_ids from existing JSONL.
    """

    if not os.path.exists(
        file_path
    ):
        return set()

    processed = set()

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as f:

        for line in f:

            try:
                record = json.loads(
                    line
                )
            except json.JSONDecodeError:
                continue

            video_id = record.get(
                "video_id"
            )

            if not video_id:
                continue

            processed.add(
                video_id
            )

    return processed

import os


def count_jsonl_records(file_path):
    """
    Count records in a JSONL file.

    Parameters
    ----------
    file_path : str

    Returns
    -------
    int
    """

    if not os.path.exists(file_path):
        return 0

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as f:

        return sum(
            1
            for _ in f
        )