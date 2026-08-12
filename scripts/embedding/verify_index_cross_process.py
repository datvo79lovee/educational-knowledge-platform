"""Rebuild MIT 6.0001 embedding index trong hai Python process độc lập.

Verifier giữ nguyên ``index_created_at_utc`` đã ghi ở M2 để timestamp không che khuất
tính deterministic của embeddings, metadata, manifest và validation report.
"""

import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BUILDER = PROJECT_ROOT / "scripts" / "embedding" / "build_mit_60001_index.py"
MANIFEST = PROJECT_ROOT / "reports" / "09_embedding" / "embedding_index_manifest.json"
OUTPUTS = (
    PROJECT_ROOT / "data" / "indexes" / "mit_60001" / "embeddings.npy",
    PROJECT_ROOT / "data" / "indexes" / "mit_60001" / "metadata.jsonl",
    MANIFEST,
    PROJECT_ROOT / "reports" / "09_embedding" / "embedding_index_validation.csv",
)
REPORT = PROJECT_ROOT / "reports" / "09_embedding" / "embedding_index_cross_process_validation.csv"


def sha256_file(path: Path) -> str:
    """Tính SHA-256 trực tiếp trên bytes của artifact."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_atomic(path: Path, content: bytes) -> None:
    """Chỉ replace report sau khi hai process đều hoàn tất."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_bytes(content)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    """Chạy builder hai lần, so hash bốn output và ghi report."""

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
        raise RuntimeError("Embedding index differs across Python processes")

    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    write_atomic(REPORT, buffer.getvalue().encode("utf-8-sig"))
    print("Embedding index cross-process deterministic: True")


if __name__ == "__main__":
    main()
