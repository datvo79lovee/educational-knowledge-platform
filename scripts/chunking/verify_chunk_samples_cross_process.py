"""Xác minh hai Python process tạo chunk experiment byte-identical."""

import csv
import argparse
import hashlib
import io
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BUILDER = PROJECT_ROOT / "scripts" / "chunking" / "build_chunk_samples.py"
SAMPLE_OUTPUT_ROOT = PROJECT_ROOT / "data" / "gold" / "mit_60001" / "samples"
FULL_OUTPUT_ROOT = PROJECT_ROOT / "data" / "gold" / "mit_60001" / "experiments"
SAMPLE_REPORT = PROJECT_ROOT / "reports" / "08_chunking" / "sample_chunk_cross_process_validation.csv"
FULL_REPORT = PROJECT_ROOT / "reports" / "08_chunking" / "full_chunk_cross_process_validation.csv"
CONFIG_IDS = ("fixed_wp240_o48_v1", "semantic_cosine_wp240_v1", "semantic_cosine_wp192_o32_v1")


def hash_output(output_root: Path, config_id: str) -> str:
    """Hash JSONL của một configuration sau mỗi process run."""

    path = output_root / config_id / "chunks.jsonl"
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

    parser = argparse.ArgumentParser(description="Verify MIT 6.0001 chunk build across Python processes.")
    parser.add_argument("--mode", choices=("sample", "full"), default="sample")
    args = parser.parse_args()
    output_root = SAMPLE_OUTPUT_ROOT if args.mode == "sample" else FULL_OUTPUT_ROOT
    report = SAMPLE_REPORT if args.mode == "sample" else FULL_REPORT
    command = [sys.executable, "-X", "utf8", str(BUILDER), "--mode", args.mode, "--single-build", "--skip-report"]
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)
    first = {config_id: hash_output(output_root, config_id) for config_id in CONFIG_IDS}
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)
    second = {config_id: hash_output(output_root, config_id) for config_id in CONFIG_IDS}
    rows = [{"chunking_config_id": config_id, "run_1_sha256": first[config_id], "run_2_sha256": second[config_id], "hashes_match": first[config_id] == second[config_id], "cross_process_deterministic": first[config_id] == second[config_id]} for config_id in CONFIG_IDS]
    if not all(row["hashes_match"] for row in rows):
        raise RuntimeError(f"{args.mode} chunk output differs across Python processes")
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    write_atomic(report, buffer.getvalue().encode("utf-8-sig"))
    print(f"Mode: {args.mode}; cross-process deterministic: True")


if __name__ == "__main__":
    main()
