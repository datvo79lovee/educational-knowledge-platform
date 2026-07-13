# Report organization

Các báo cáo được chia theo milestone để tránh trộn dữ liệu đầu ra của các bước.

## `01_data_audit`

Audit PostgreSQL, transcript và checkpoint trước khi phân tích corpus.

```text
video_summary.csv
transcript_summary.csv
checkpoint_status_summary.csv
video_transcript_summary.csv
```

## `02_corpus_analysis`

Phân tích course, domain và transcript ngắn từ metadata hiện có.

```text
transcript_classification.csv
course_distribution.csv
transcript_distribution.csv
short_transcript_review.csv
```

## `03_playlist_mapping`

Khôi phục quan hệ nhiều–nhiều giữa 290 video transcript và public playlists.

```text
playlists.csv
video_playlist.csv
playlist_coverage.csv
playlist_distribution.csv
```

## `04_scope_decision`

Inventory, gap report và target manifest của MIT 6.0001. Folder hiện có README mô
tả output dự kiến; CSV sẽ được tạo ở bước inventory.

## `05_target_corpus`

Trạng thái targeted transcript acquisition của MIT 6.0001. Raw transcript không
được lưu trong reports.

Các script tạo báo cáo phải ghi trực tiếp vào folder milestone tương ứng. Không tạo
thêm CSV ở thư mục gốc `reports/`.
