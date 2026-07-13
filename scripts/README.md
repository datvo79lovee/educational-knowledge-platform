# Operational scripts

Các script được nhóm theo chức năng. Chạy lệnh từ project root.

## `transcript_loading`

Load Bronze transcript payload vào PostgreSQL.

```powershell
python scripts/transcript_loading/load_transcripts_to_postgresql.py
python scripts/transcript_loading/load_transcripts_to_postgresql.py --commit
```

Lệnh không có `--commit` là dry-run và rollback. Chỉ dùng `--commit` sau khi kiểm
tra số lượng insert dự kiến.

## `data_audit`

Audit PostgreSQL và checkpoint, không sửa database.

```powershell
python scripts/data_audit/audit_corpus.py
python scripts/data_audit/export_video_transcript_summary.py
```

Output:

```text
reports/01_data_audit/
```

## `corpus_analysis`

Phân loại course/domain bằng metadata heuristic, không ghi nhãn vào database.

```powershell
python scripts/corpus_analysis/analyze_corpus.py
```

Output:

```text
reports/02_corpus_analysis/
```

## `playlist_mapping`

Gọi YouTube Data API để lấy public playlists và mapping với 290 transcript video.
Script có cache và checkpoint trong Bronze.

```powershell
python scripts/playlist_mapping/map_playlists.py
```

Output:

```text
reports/03_playlist_mapping/
```

## `target_corpus`

Chứa các script dành riêng cho MIT 6.0001. Chưa có executable cho đến khi triển
khai target inventory.

Không chạy `git add .` sau khi tạo output. Kiểm tra từng nhóm code, report và docs
trước khi stage.
