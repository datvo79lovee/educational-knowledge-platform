# Silver transcript contract v1

## Trạng thái

Đã chốt và full build đạt ngày 2026-07-26.

```text
schema_version: silver_transcript_v1
cleaning_version: mit_60001_clean_v1
scope_version: mit_60001_fall_2016_v1
```

Contract này áp dụng cho 38 video trong target manifest v1. Nó không tự động mở
rộng sang 286 transcript ngoài scope.

## Mục tiêu

Silver transcript phải:

- tái tạo được từ Bronze payload và target manifest;
- giữ timing gốc để chunk có thể citation đúng thời điểm;
- giữ metadata language và `is_generated`;
- phát hiện thay đổi nguồn hoặc nội dung bằng SHA-256;
- không phụ thuộc vào schema PostgreSQL để lấy segment;
- cho kết quả giống nhau khi chạy lại cùng input và cùng cleaning version.

## Định dạng file

```text
data/silver/mit_60001/transcripts_clean.jsonl
```

Quy tắc vật lý:

- UTF-8, không BOM;
- một JSON object trên mỗi dòng;
- line ending LF;
- một record cho mỗi `video_id` trong manifest;
- thứ tự record theo `playlist_position` từ 0 đến 37;
- không có duplicate `video_id`;
- không ghi record nếu validation của record thất bại.

File Silver là output có thể tái tạo và nằm trong `data/silver/`, không commit vào
Git. Contract, code và report validation phải được commit.

## Document schema

| Field | Kiểu | Bắt buộc | Nguồn hoặc quy tắc |
| --- | --- | --- | --- |
| `schema_version` | string | Có | Hằng số `silver_transcript_v1` |
| `scope_version` | string | Có | `target_manifest.csv` |
| `cleaning_version` | string | Có | Hằng số `mit_60001_clean_v1` |
| `playlist_id` | string | Có | Target manifest |
| `playlist_position` | integer | Có | Target manifest, 0–37 |
| `video_id` | string | Có | Bronze và manifest phải trùng |
| `title` | string | Có | Title đã đóng băng trong manifest |
| `language_code` | string | Có | Bronze `language_code`; hiện là `en` |
| `language_name` | string | Có | Bronze `language`, giữ metadata nguồn |
| `is_generated` | boolean | Có | Bronze `is_generated` |
| `fetched_at` | date-time string | Có | Bronze `fetched_at` |
| `segment_count` | integer | Có | Phải bằng số phần tử trong `segments` |
| `transcript_text` | string | Có | Nối cleaned segment text bằng newline |
| `transcript_length` | integer | Có | `len(transcript_text)` theo Unicode code point |
| `content_sha256` | string | Có | Hash canonical cleaned content |
| `lineage` | object | Có | File nguồn và source payload hash |
| `segments` | array | Có | Cleaned segments giữ timing gốc |

Không thêm `description`, `publish_date` hoặc view count vào Silver transcript.
Các field đó thuộc video metadata và có thể JOIN bằng `video_id`.

## Segment schema

| Field | Kiểu | Bắt buộc | Quy tắc |
| --- | --- | --- | --- |
| `segment_index` | integer | Có | Liên tục từ 0 sau cleaning |
| `source_segment_index` | integer | Có | Vị trí segment trong Bronze |
| `text` | string | Có | Không rỗng sau cleaning |
| `start_second` | number | Có | Sao chép từ Bronze `start`, không làm tròn |
| `duration_second` | number | Có | Sao chép từ Bronze `duration`, phải lớn hơn 0 |

Không lưu `end_second` trong Silver transcript vì đây là giá trị dẫn xuất:

```text
end_second = start_second + duration_second
```

Chunking pipeline có thể tính `end_second` khi tạo chunk. Không sửa timing để loại
1.450 cặp segment overlap đã quan sát trong Bronze.

## Lineage schema

| Field | Giá trị |
| --- | --- |
| `bronze_file` | `data/bronze/transcripts_raw.jsonl` |
| `manifest_file` | `reports/04_scope_decision/target_manifest.csv` |
| `source_payload_sha256` | SHA-256 của JSONL source line, bỏ line ending |

`source_payload_sha256` dùng để phát hiện Bronze payload đã thay đổi. Hash được tính
trên byte UTF-8 của chính JSON object trong source line sau khi chỉ bỏ `\r`/`\n` ở
cuối dòng; không parse rồi serialize lại trước khi hash.

## Content hash

`content_sha256` phát hiện thay đổi text hoặc timing sau cleaning.

Đầu vào hash gồm:

```json
{
  "language_code": "en",
  "segments": [
    {
      "duration_second": 2.4,
      "source_segment_index": 0,
      "start_second": 0.79,
      "text": "cleaned segment text"
    }
  ],
  "video_id": "example_video_id"
}
```

Canonical serialization trong Python:

```python
json.dumps(
    hash_input,
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
    allow_nan=False,
).encode("utf-8")
```

Sau đó tính SHA-256 và lưu 64 ký tự hexadecimal viết thường. Không đưa
`cleaning_version` vào content hash: nếu hai version tạo cùng nội dung và timing,
hash được phép giống nhau; version vẫn được lưu riêng để truy vết pipeline.

## Invariants bắt buộc

Mỗi record phải thỏa mãn:

1. `video_id`, `playlist_id`, `playlist_position` và title khớp manifest.
2. `scope_version` đúng `mit_60001_fall_2016_v1`.
3. `segment_count == len(segments)` và lớn hơn 0.
4. `segment_index` liên tục từ 0.
5. `source_segment_index` tăng dần và không lặp.
6. `text.strip()` không rỗng. Với `mit_60001_clean_v1`, `text` phải bằng chính
   xác Bronze `segments[source_segment_index].text`; không normalize Unicode,
   whitespace hoặc newline.
7. `start_second >= 0` và không giảm theo source order.
8. `duration_second > 0`.
9. Overlap timing được phép và phải giữ nguyên.
10. `transcript_text` bằng phép nối `segment.text` theo thứ tự bằng `\n`.
11. `transcript_length == len(transcript_text)`.
12. `source_payload_sha256` và `content_sha256` phải tính lại khớp record.
13. `fetched_at` parse được theo ISO-8601 và có timezone.
14. Không có field ngoài JSON Schema v1.

Validation toàn file phải xác nhận:

- đúng 38 record và 38 `video_id` duy nhất;
- position liên tục 0–37;
- không video ngoài manifest;
- mọi video trong manifest có đúng một Silver record;
- output chạy lại từ cùng input có cùng content hash và cùng byte content.

## Language policy

`language_code` là field chuẩn để lọc ngôn ngữ. `language_name` chỉ là metadata
nguồn vì audit đã thấy hai giá trị:

```text
English - CC
English - CC (English)
```

Không chuẩn hóa hai tên này thành một chuỗi mới trong v1; giữ nguyên để truy vết.

## Timestamp policy

`fetched_at` giữ timestamp nguồn, không thay bằng thời điểm cleaning. Không thêm
`processed_at` vào từng record vì timestamp chạy sẽ làm output khác nhau giữa hai
lần build giống nhau. Thời điểm chạy pipeline được ghi trong report riêng.

## Cleaning boundary của contract

Schema v1 có field `segments[].text` để các cleaning version tương lai có thể lưu
text đã được biến đổi theo policy riêng. Tuy nhiên, với
`cleaning_version=mit_60001_clean_v1`, Silver `segments[].text` bắt buộc bằng
chính xác Bronze `segments[source_segment_index].text` tương ứng. V1 không cho
phép bất kỳ transformation text nào.

Chỉ một cleaning version mới, có policy mới và sample validation đạt, mới được phép
thay đổi text. Dù ở version nào, pipeline không được thay đổi `start_second`,
`duration_second`, language, `is_generated` hoặc manifest metadata.

Quy tắc text cụ thể đã được chốt tại:

```text
docs/design/SILVER_CLEANING_POLICY.md
```

Full cleaning đã chạy đạt ngày 2026-07-26 sau khi sample validation đạt:

```text
Records: 38/38
Positions: 0..37
Total segments: 12,518
Full output SHA-256: 50d559529bedc33715b13312c5e4b7def80ac808521b53699a14465e084a8ecb
```

Chi tiết validation nằm tại `reports/07_cleaning/full_validation.csv` và
`reports/07_cleaning/cleaning_summary.csv`.

## Quan hệ với semantic chunking

Silver giữ timing ở cấp segment để truy vết citation; timing không phải quy tắc
chia chunk. Chunking phase sau sẽ gom các segment liên tiếp theo semantic boundary,
dùng token limit làm guardrail và lấy `start_second`/`end_second` từ segment đầu,
cuối của chunk.

Cleaning không dựng câu bằng phỏng đoán và không quyết định semantic boundary.
Nếu chunker cần text chuẩn hóa riêng để tính embedding similarity, đó phải là một
derived view; `segments[].text` trong Silver vẫn tuân theo Cleaning Policy v1.

## Machine-readable schema

```text
schemas/silver_transcript_v1.schema.json
```

JSON Schema kiểm tra shape và kiểu dữ liệu. Các invariant liên record, hash,
segment index và phép nối transcript phải được kiểm tra thêm bằng validator Python.
