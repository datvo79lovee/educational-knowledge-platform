# Tài liệu dự án

Tài liệu được tổ chức theo mục đích. Người mới nên đọc theo thứ tự dưới đây.

## 1. Trạng thái hiện tại

- `status/CURRENT_STATUS.md`: số liệu và quyết định đang có hiệu lực.
- `progress_log.md`: nhật ký xây dựng theo từng ngày.

## 2. Quyết định phạm vi

- `decisions/CORPUS_SCOPE.md`: lý do chọn MIT 6.0001 Fall 2016 và ranh giới corpus.

## 3. Kế hoạch triển khai

- `plans/MIT_60001_IMPLEMENTATION_PLAN.md`: các phase từ inventory đến evaluation.
- `project_plan.md`: kế hoạch lịch sử của toàn dự án.

## 4. Báo cáo đã hoàn thành

```text
reports/
├── 01_data_audit/
├── 02_corpus_analysis/
├── 03_playlist_mapping/
├── 04_scope_decision/
└── 05_target_corpus/
```

- `reports/01_data_audit/`: load PostgreSQL và audit data foundation.
- `reports/02_corpus_analysis/`: phân tích course/domain và transcript ngắn.
- `reports/03_playlist_mapping/`: khôi phục quan hệ video–playlist.
- `reports/04_scope_decision/`: target inventory, gap report và manifest MIT 6.0001.
- `reports/05_target_corpus/`: baseline và kết quả targeted transcript acquisition.

## 5. Kiến trúc và database

- `architecture.md`: kiến trúc tổng thể hiện có.
- `postgresql_loading_plan.md`: kế hoạch load metadata video.

Các báo cáo CSV tương ứng nằm trong thư mục `reports/` ở project root và dùng cùng
số thứ tự milestone.
