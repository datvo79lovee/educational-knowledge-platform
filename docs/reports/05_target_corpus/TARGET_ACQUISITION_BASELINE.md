# Baseline targeted transcript acquisition

## Ngày thực hiện

2026-07-16

## Trạng thái

Target crawler đã được xây dựng và kiểm tra ở planning mode. Chưa có transcript
request nào được thực hiện trong bước này.

## Scope

```text
scope_version: mit_60001_fall_2016_v1
playlist_id: PLUl4u3cNGP63WbdFxL8giv4yhgdMGaZNA
manifest videos: 38
reviewed fetch candidates: 34
payload available: 4
```

## Script

```text
scripts/target_corpus/fetch_target_transcripts.py
```

## Guardrails

- Mặc định không gọi transcript API.
- Phải truyền `--execute` để bật request.
- Chỉ nhận video nằm trong manifest v1.
- Chỉ nhận video được gap report đánh dấu `fetch_candidate=True`.
- Bỏ qua payload đã tồn tại trong Bronze.
- Bỏ qua trạng thái cố định như `success`, `no_transcript` và
  `transcripts_disabled`.
- Checkpoint ghi thêm `scope_version` và `pipeline=target_corpus`.
- Dừng ngay khi gặp IP block, request block hoặc rate limit.
- Hỗ trợ giới hạn queue, runtime và số lỗi liên tiếp.

## Baseline planning result

```text
payload_available: 4
not_attempted: 34
queued_videos: 34
```

Planning mode đã liệt kê đúng các playlist position còn thiếu và không ghi Bronze
hoặc checkpoint.

## Guardrail tests

- Video ID ngoài manifest: bị từ chối.
- Video đã có transcript nhưng không phải fetch candidate: bị từ chối.
- Cả hai trường hợp đều kết thúc trước transcript request.

## Report outputs

```text
reports/05_target_corpus/acquisition_status.csv
reports/05_target_corpus/acquisition_summary.csv
```

Report được tạo lại từ trạng thái Bronze/checkpoint hiện tại sau mỗi lần chạy.

## Lệnh planning

```powershell
python scripts/target_corpus/fetch_target_transcripts.py
```

## Lệnh test được đề xuất

Không chạy cả 34 video ngay. Lần đầu chỉ chạy tối đa 3 video:

```powershell
python scripts/target_corpus/fetch_target_transcripts.py `
  --execute `
  --limit 3 `
  --min-delay 20 `
  --max-delay 60 `
  --max-runtime-minutes 10
```

Sau test phải kiểm tra:

- payload mới trong Bronze JSONL;
- checkpoint status;
- segment count, language và `is_generated`;
- acquisition status report;
- không có video ngoài manifest.

Chỉ chạy phần còn lại sau khi test nhỏ đạt điều kiện.
