"""Xác minh hai process promote canonical Gold tạo output byte-identical.

Một lần chạy lại trong cùng process chưa chứng minh đầy đủ tính deterministic.
Script này khởi động promoter hai lần bằng hai Python subprocess độc lập, hash ba
artifact quan trọng sau mỗi lần và fail nếu bất kỳ bytes nào khác nhau.
"""

import csv
import hashlib
import io
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROMOTER = PROJECT_ROOT / "scripts" / "chunking" / "promote_selected_config.py"
# Kiểm cả generated Gold lẫn hai artifact mô tả nó. Nếu manifest/report chứa giá trị
# phụ thuộc thời gian hoặc thứ tự không ổn định, phép so sánh này cũng sẽ phát hiện.
OUTPUTS = (
    PROJECT_ROOT / "data" / "gold" / "mit_60001" / "chunks.jsonl",
    PROJECT_ROOT / "reports" / "08_chunking" / "canonical_gold_manifest.json",
    PROJECT_ROOT / "reports" / "08_chunking" / "canonical_gold_validation.csv",
)
REPORT = PROJECT_ROOT / "reports" / "08_chunking" / "canonical_gold_cross_process_validation.csv"


def sha256_file(path: Path) -> str:
    """Tính SHA-256 trực tiếp trên bytes của một output."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_atomic(path: Path, content: bytes) -> None:
    """Chỉ replace cross-process report sau khi nội dung hoàn chỉnh."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_bytes(content)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    """Chạy hai subprocess, so hash và ghi report kết quả."""

    # Dùng chính interpreter hiện tại để hai lần chạy có cùng Python environment.
    command = [sys.executable, "-X", "utf8", str(PROMOTER)]
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)
    first = {path.name: sha256_file(path) for path in OUTPUTS}

    # Lần hai ghi đè cùng các output. Hash sau lần này phải giống lần một tuyệt đối.
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
        raise RuntimeError("Canonical Gold promotion differs across Python processes")
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    write_atomic(REPORT, buffer.getvalue().encode("utf-8-sig"))
    print("Canonical Gold promotion cross-process deterministic: True")


if __name__ == "__main__":
    main()
