# Trạng thái hiện tại

## Ngày ghi nhận

2026-07-12

## Số lượng dữ liệu

- Nguồn trong PostgreSQL: 1
- Video trong PostgreSQL: 8.021
- Transcript thành công trong Bronze JSONL: 290
- Transcript trong PostgreSQL: 290
- Lỗi lấy transcript mới nhất (`fetch_failed`): 1
- Không có transcript (`no_transcript`): 5
- Transcript bị tắt (`transcripts_disabled`): 5
- Bị chặn IP mới nhất (`ip_blocked`): 1
- Tổng số dòng checkpoint: 304
- Số video duy nhất xuất hiện trong checkpoint: 302

Checkpoint là append-only. Có 2 dòng lịch sử `fetch_failed` và 2 dòng lịch sử
`ip_blocked`, nhưng mỗi trạng thái này chỉ thuộc 1 video duy nhất bị ghi lại hai lần.

## Vị trí dữ liệu hiện có

- PostgreSQL: đã nạp `sources`, `videos` và 290 `transcripts`.
- Transcript Bronze JSONL: `data/bronze/transcripts_raw.jsonl`
- Checkpoint transcript: `data/bronze/transcripts_checkpoint.jsonl`
- Báo cáo JOIN video và transcript: `reports/video_transcript_summary.csv`

## Các vấn đề đã biết

- Video được thu thập theo toàn bộ channel nhưng không lưu quan hệ playlist.
- Cả Bronze JSONL và PostgreSQL hiện đều có 290 transcript thành công.
- Chưa audit quan hệ playlist và độ phủ chủ đề của corpus.
- Playlist chỉ là metadata hỗ trợ phân loại, không phải nhãn chủ đề tuyệt đối.
- Schema hiện tại chưa lưu tên ngôn ngữ đầy đủ, trạng thái transcript tự động,
  số segment, thời gian của từng segment và content hash.

## Quy tắc đóng băng

Không sửa schema, transcript pipeline, chunking, embedding hoặc Search API trước
khi hoàn thành audit corpus hiện tại và độ phủ playlist.

## Quyết định hiện tại

Không crawl lại toàn bộ channel. Giữ nguyên các transcript hiện có, khôi phục riêng
quan hệ giữa video và playlist, sau đó chỉ crawl bổ sung có mục tiêu nếu báo cáo
độ phủ corpus xác nhận có phần dữ liệu cụ thể còn thiếu.
