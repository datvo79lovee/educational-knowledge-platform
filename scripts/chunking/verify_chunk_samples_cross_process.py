"""Xác minh hai Python process tạo Gold sample byte-identical."""

import csv
import hashlib
import io
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BUILDER = PROJECT_ROOT / "scripts" / "chunking" / "build_chunk_samples.py"
OUTPUT_ROOT = PROJECT_ROOT / "data" / "gold" / "mit_60001" / "samples"
REPORT = PROJECT_ROOT / "reports" / "08_chunking" / "sample_chunk_cross_process_validation.csv"
CONFIG_IDS = ("fixed_wp240_o48_v1", "semantic_cosine_wp240_v1", "semantic_cosine_wp192_o32_v1")


def hash_output(config_id: str) -> str:
    """Hash JSONL của một configuration sample sau mỗi process run."""

    path = OUTPUT_ROOT / config_id / "chunks.jsonl"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_atomic(path: Path, content: bytes) -> None:
    """Ghi report hoàn chỉnh trước khi replace file chính."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_bytes(content)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    """Run builder hai lần độc lập rồi so sánh SHA-256 từng configuration."""

    command = [sys.executable, "-X", "utf8", str(BUILDER), "--single-build", "--skip-report"]
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)
    first = {config_id: hash_output(config_id) for config_id in CONFIG_IDS}
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)
    second = {config_id: hash_output(config_id) for config_id in CONFIG_IDS}
    rows = [{"chunking_config_id": config_id, "run_1_sha256": first[config_id], "run_2_sha256": second[config_id], "hashes_match": first[config_id] == second[config_id], "cross_process_deterministic": first[config_id] == second[config_id]} for config_id in CONFIG_IDS]
    if not all(row["hashes_match"] for row in rows):
        raise RuntimeError("Sample chunk output differs across Python processes")
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    write_atomic(REPORT, buffer.getvalue().encode("utf-8-sig"))
    print("Cross-process deterministic: True")


if __name__ == "__main__":
    main()
