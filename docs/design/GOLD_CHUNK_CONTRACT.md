# Gold chunk contract v1

## Trạng thái

Đã chốt cho chunking experiment ngày 2026-07-27. Contract chưa tạo Gold dataset.

```text
schema_version: gold_chunk_v1
scope_version: mit_60001_fall_2016_v1
silver_schema_version: silver_transcript_v1
silver_cleaning_version: mit_60001_clean_v1
chunking_version: mit_60001_chunk_v1
```

## Phạm vi

Gold chunk là output dẫn xuất dùng cho retrieval. Mỗi record phải truy ngược đến
một Silver video và dải segment liên tiếp. Contract chỉ áp dụng cho 38 video trong
target manifest v1; không chunk 286 transcript ngoài scope.

```text
Input:  data/silver/mit_60001/transcripts_clean.jsonl
Output: data/gold/mit_60001/<chunking_config_id>/chunks.jsonl
```

Gold JSONL là generated data, không commit. Contract, schema, builder và report
validation được commit.

## Field bắt buộc

| Field | Quy tắc |
| --- | --- |
| `schema_version` | `gold_chunk_v1` |
| `scope_version` | `mit_60001_fall_2016_v1` |
| `silver_schema_version` | `silver_transcript_v1` |
| `silver_cleaning_version` | `mit_60001_clean_v1` |
| `chunking_version` | `mit_60001_chunk_v1` |
| `chunking_config_id` | Định danh bất biến của cấu hình experiment |
| `chunk_id` | `{video_id}:{chunking_config_id}:{chunk_index}` |
| `playlist_id`, `playlist_position`, `video_id`, `title` | Sao chép từ Silver |
| `chunk_index` | Liên tục từ 0 trong một video/configuration |
| `source_segment_start_index`, `source_segment_end_index` | Dải Silver segment, bao gồm hai đầu |
| `source_segment_count` | `end - start + 1` |
| `chunk_text` | Nối nguyên văn `segment.text` bằng `\n` |
| `chunk_length` | `len(chunk_text)` theo Unicode code point |
| `start_second` | Timing nguyên gốc của segment đầu |
| `end_second` | Timing dẫn xuất từ segment cuối |
| `content_sha256` | Hash canonical của nội dung chunk và range/timing |
| `lineage` | `silver_file` và `silver_content_sha256` nguồn |

Không lưu embedding, retrieval score, LLM answer, timestamp chạy pipeline hay video
description trong Gold chunk v1.

## Quy tắc lineage, text và segment

`lineage` có dạng:

```json
{
  "silver_file": "data/silver/mit_60001/transcripts_clean.jsonl",
  "silver_content_sha256": "SHA-256 từ Silver record nguồn"
}
```

1. Một chunk chỉ chứa segment của một video.
2. Segment trong chunk liên tiếp, tăng dần, không lặp.
3. `chunk_text` phải đúng bằng phép nối text của source range.
4. Không strip, normalize whitespace, deduplicate, dịch hoặc sửa code.
5. Các chunk khác nhau có thể overlap nếu configuration khai báo; mọi Silver segment
   phải được cover ít nhất một lần trong mỗi configuration.
6. Khi Silver content hash đổi, toàn bộ Gold output liên quan phải rebuild.

## Citation timing

```text
start_second = start_second của segment đầu
end_second = start_second + duration_second của segment cuối
```

Không làm tròn hoặc sửa timing nguồn. Để tránh lỗi biểu diễn float, builder tính end
bằng `Decimal(str(start_second)) + Decimal(str(duration_second))`, sau đó serialize
số JSON tối thiểu tương đương. Ví dụ `2575.55 + 1.61` phải ghi `2577.16`, không ghi
`2577.1600000000003`. Timing overlap giữa Silver segment được phép.

## Content hash

`content_sha256` là SHA-256 của canonical UTF-8 JSON gồm `video_id`,
`chunking_config_id`, source range, `chunk_text`, `start_second` và `end_second`.
Serialization dùng `ensure_ascii=False`, `sort_keys=True`, `separators=(",", ":")`
và `allow_nan=False`.

## Validation bắt buộc

Ngoài JSON Schema, validator phải kiểm tra metadata khớp Silver/manifest, chunk ID
duy nhất, index liên tục, source range, text, length, timing, hash, lineage, coverage
segment và deterministic rebuild. Report không được chứa `chunk_text` hoặc transcript
text.

## Quan hệ với experiment

Contract không quyết định semantic boundary hoặc token limit. Mỗi configuration dùng
`chunking_config_id` riêng để fixed-token baseline và semantic strategies dùng chung
schema, validator và cách đánh giá. Ba configuration được chốt ở Milestone 3.
