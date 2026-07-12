# Báo cáo nạp transcript vào PostgreSQL

## Ngày thực hiện

2026-07-12

## Kết quả

Toàn bộ 290 transcript thành công trong Bronze JSONL đã được kiểm tra và commit
vào PostgreSQL. Sau khi nạp, phép JOIN giữa `transcripts` và `videos` trả về đủ
290 dòng. Kết quả JOIN được xuất ra
`reports/video_transcript_summary.csv`.

## Dữ liệu nguồn

- File đầu vào: `data/bronze/transcripts_raw.jsonl`
- Tổng số bản ghi đầu vào: 290
- Số `video_id` duy nhất: 290
- Tổng số segment: 205.739
- Bản ghi không có segment: 0
- Segment có nội dung rỗng: 0
- Giá trị `fetched_at` không hợp lệ: 0

## Kiểm tra trước khi nạp

- Số transcript đã có trong PostgreSQL: 0
- `video_id` đầu vào không tồn tại trong bảng `videos`: 0
- `video_id` trùng trong dữ liệu đầu vào: 0
- Số bản ghi dự kiến thêm trong dry-run: 290
- Tổng số bản ghi tạm thời sau dry-run: 290
- Transaction dry-run: đã rollback thành công, không ghi dữ liệu

## Ánh xạ trường dữ liệu

| Bronze JSONL | PostgreSQL `transcripts` | Quy tắc |
| --- | --- | --- |
| `video_id` | `video_id` | Giữ nguyên |
| `language_code` | `language` | Lưu `en`, phù hợp giới hạn `VARCHAR(20)` hiện tại |
| `segments[].text` | `raw_text` | Ghép các segment không rỗng bằng ký tự xuống dòng |
| `fetched_at` | `retrieved_at` | Chuyển thành timestamp có múi giờ |

## Kết quả nạp

- Số dòng trước khi nạp: 0
- Số dòng đã thêm: 290
- Số dòng sau khi nạp: 290
- Số dòng trả về từ JOIN video và transcript: 290
- Transcript có nội dung rỗng: 0
- Độ dài transcript nhỏ nhất: 439 ký tự
- Độ dài transcript lớn nhất: 101.387 ký tự
- Phân bố ngôn ngữ đã lưu: `en` = 290

## Khả năng chạy lại không tạo dữ liệu trùng

Loader kiểm tra `video_id` đã có trong bảng `transcripts` trước khi thêm. Khi chạy
lại, loader bỏ qua 290 video đã tồn tại và không tạo thêm bản ghi.

Schema database hiện chưa có unique constraint cho `transcripts.video_id`. Vì vậy,
khả năng chống trùng hiện chỉ được bảo đảm bởi loader, chưa được database cưỡng chế.

## Thông tin chưa được biểu diễn trong schema hiện tại

Các trường Bronze sau chưa được nạp vì bảng `transcripts` chưa có cột tương ứng:

- tên ngôn ngữ mô tả trong trường `language`
- `is_generated`
- số lượng segment
- `start` và `duration` của từng segment
- content hash

Mảng segment đầy đủ vẫn được giữ trong Bronze JSONL, là nguồn dữ liệu gốc. Không
có thay đổi schema nào được thực hiện trong lần nạp này.

## File được tạo hoặc cập nhật

- Loader: `scripts/load_transcripts_to_postgresql.py`
- Script xuất báo cáo: `scripts/export_video_transcript_summary.py`
- Báo cáo JOIN: `reports/video_transcript_summary.csv`
- Trạng thái hiện tại: `docs/CURRENT_STATUS.md`

## Việc cần làm tiếp theo

Chưa thực hiện chunking. Trước tiên cần audit 290 bản ghi đã JOIN theo title,
description, ngày xuất bản, ngôn ngữ và độ dài transcript. Sau đó cần khôi phục
quan hệ giữa video và playlist.

Kết quả audit sẽ cho biết corpus hiện tại là một tập khóa học có phạm vi rõ ràng
hay chỉ là mẫu dữ liệu rải rác lấy từ toàn bộ channel.
