"""Xác minh lexical index build byte-identical qua hai Python processes."""

import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BUILDER = PROJECT_ROOT / "scripts" / "retrieval" / "build_mit_60001_lexical_index.py"
MANIFEST = PROJECT_ROOT / "reports" / "10_retrieval" / "lexical_index_manifest.json"
OUTPUTS = (
    PROJECT_ROOT / "data" / "indexes" / "mit_60001" / "lexical_index.json",
    MANIFEST,
    PROJECT_ROOT / "reports" / "10_retrieval" / "lexical_index_validation.csv",
)
REPORT = PROJECT_ROOT / "reports" / "10_retrieval" / "lexical_index_cross_process_validation.csv"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_bytes(content)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    created_at = json.loads(MANIFEST.read_text(encoding="utf-8"))["index_created_at_utc"]
    command = [
        sys.executable,
        "-X",
        "utf8",
        str(BUILDER),
        "--created-at-utc",
        created_at,
    ]
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)
    first = {path.name: sha256_file(path) for path in OUTPUTS}
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)
    second = {path.name: sha256_file(path) for path in OUTPUTS}
    rows = [
        {
            "artifact": path.name,
            "run_1_sha256": first[path.name],
            "run_2_sha256": second[path.name],
            "hashes_match": first[path.name] == second[path.name],
            "cross_process_deterministic": first[path.name] == second[path.name],
        }
        for path in OUTPUTS
    ]
    if not all(row["hashes_match"] for row in rows):
        raise RuntimeError("Lexical index differs across Python processes")
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    write_atomic(REPORT, buffer.getvalue().encode("utf-8-sig"))
    print("Lexical index cross-process deterministic: True")


if __name__ == "__main__":
    main()
