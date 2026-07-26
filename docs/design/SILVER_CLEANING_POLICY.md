# Silver cleaning policy v1

## Trạng thái

Đã chốt và full build đạt ngày 2026-07-26.

```text
cleaning_version: mit_60001_clean_v1
schema_version: silver_transcript_v1
scope_version: mit_60001_fall_2016_v1
```

Policy áp dụng cho 38 target payload đã audit. Sample validation đã đạt trước khi
full cleaning chạy ngày 2026-07-26; kết quả full nằm tại
`reports/07_cleaning/cleaning_summary.csv`.

## Mục tiêu

Cleaning v1 tạo record có cấu trúc, lineage và hash mà không tự sửa nội dung phụ đề.
Độ chính xác nội dung được ưu tiên hơn việc làm text trông đẹp hoặc giống văn viết.

V1 là lossless text policy:

- giữ nguyên từng `segments[].text` của target Bronze payload;
- giữ nguyên thứ tự và timing;
- không xóa hoặc gộp segment;
- chỉ validate, ánh xạ field, tạo derived text và hash.

## Bằng chứng từ Bronze audit

Nguồn máy đọc được:

```text
reports/07_cleaning/bronze_audit_summary.csv
reports/07_cleaning/bronze_payload_profile.csv
```

```text
Target payloads: 38
Segments: 12.518
Empty segments: 0
Segments có LF: 9.048
Segments có CR: 0
Segments có tab: 0
Segments có NBSP: 0
Segments có zero-width character: 0
Segments sai Unicode NFC: 0
Segments có khoảng trắng thừa: 0
Caption cue dạng [..]: 7
Exact adjacent duplicates: 7
Normalized adjacent duplicates: 0
Adjacent containment pairs: 15
Timing overlap pairs: 1.450
```

Vì input hiện không có lỗi whitespace hoặc Unicode cần sửa, thêm normalization
mạnh sẽ tạo rủi ro nhưng không giải quyết vấn đề quan sát được.

## Thứ tự xử lý bắt buộc

### 1. Validate scope và source

- Đọc đúng target manifest v1.
- Yêu cầu đúng 38 payload và 38 `video_id` duy nhất.
- Từ chối video ngoài manifest.
- Yêu cầu mỗi manifest video có đúng một Bronze payload.
- Tính `source_payload_sha256` từ source JSONL line trước khi parse/transform.

### 2. Validate payload schema

Yêu cầu đủ:

```text
video_id
language_code
language
is_generated
segments
fetched_at
```

Sai field bắt buộc, sai kiểu hoặc timestamp không parse được làm pipeline thất bại.

### 3. Validate segment schema

Mỗi segment phải có:

```text
text: string không rỗng
start: number >= 0
duration: number > 0
```

`start` không được giảm theo source order. Timing overlap được phép.

### 4. Ánh xạ lossless

```text
segment_index        = vị trí output liên tục từ 0
source_segment_index = vị trí segment trong Bronze
text                 = Bronze text, giữ nguyên
start_second         = Bronze start, giữ nguyên
duration_second      = Bronze duration, giữ nguyên
```

Với corpus v1 không có segment rỗng, do đó:

```text
segment_index == source_segment_index
```

Nếu lần build sau xuất hiện segment rỗng, pipeline phải dừng và báo cáo. Không tự
xóa segment vì việc đó làm thay đổi lineage và có thể che giấu source drift.

### 5. Tạo transcript text

```python
transcript_text = "\n".join(segment["text"] for segment in segments)
```

Không strip, collapse whitespace hoặc thay internal newline. Newline dùng để nối
hai segment là ký tự mới thêm; newline nằm sẵn trong segment vẫn được giữ nguyên.

### 6. Tạo hash

- Tính `source_payload_sha256` theo Silver Transcript Contract.
- Tính `content_sha256` từ cleaned segment text và timing bằng canonical JSON.
- Kiểm tra lại hash trước khi ghi output.

### 7. Validate toàn file và ghi atomically

- Validate từng record bằng JSON Schema v1.
- Kiểm tra invariant mà JSON Schema không biểu diễn được.
- Kiểm tra đủ 38 record theo position 0–37.
- Ghi file tạm trong cùng output directory.
- Chỉ replace output chính sau khi toàn bộ validation pass.
- Nếu có lỗi, giữ nguyên output Silver cũ nếu nó tồn tại.

## Transformation được phép trong v1

V1 không thay đổi segment text. Các thao tác được phép chỉ gồm:

- đổi tên field theo contract;
- thêm manifest metadata;
- thêm `segment_index` và `source_segment_index`;
- tạo `transcript_text`, `transcript_length`;
- tạo lineage và hash;
- serialize JSONL theo thứ tự ổn định.

## Transformation bị cấm trong v1

Không được:

- sửa chính tả hoặc từ transcript nhận sai;
- thêm, xóa hoặc đổi punctuation;
- đổi viết hoa/thường;
- xóa filler words;
- dịch nội dung;
- tự sửa tên biến, keyword, toán tử hoặc indentation;
- collapse whitespace bằng regex;
- xóa internal newline;
- decode/encode HTML theo phỏng đoán;
- xóa caption cue như `[Music]`;
- deduplicate segment giống nhau hoặc chứa lẫn nhau;
- ghép hoặc tách segment;
- tái dựng câu bằng LLM;
- thay đổi, làm tròn hoặc sửa timing overlap.

## Phân loại validation

### Hard failure

- thiếu hoặc trùng target payload;
- video ngoài scope;
- schema/kiểu dữ liệu sai;
- segment text rỗng;
- timing âm, duration không dương hoặc start sai thứ tự;
- timestamp không hợp lệ;
- source/content hash không khớp;
- output không đủ 38 record;
- output không deterministic khi chạy lại cùng input.

### Report-only observation

- segment có internal newline;
- timing overlap;
- caption cue;
- exact adjacent duplicate;
- adjacent text containment;
- hai biến thể `language_name`;
- transcript ngắn hoặc dài.

Report-only observation không được tự động sửa hoặc làm pipeline thất bại.

## Quan hệ với semantic chunking

Cleaning không chia semantic chunk. Phase chunking sẽ:

- chỉ gom các segment liên tiếp;
- dùng semantic similarity để tìm candidate boundary;
- dùng token min/max làm guardrail;
- giữ source segment range;
- tính timestamp chunk từ segment đầu và cuối;
- so sánh semantic strategy với fixed-token baseline bằng evaluation.

Timing được giữ cho citation, không được dùng làm boundary chính.

## Sample validation bắt buộc

Sample implementation phải gồm ít nhất năm trường hợp:

| Vai trò | Video ID | Lý do |
| --- | --- | --- |
| Language variant và duplicate | `nykOeWgQcHM` | Tên language khác, có duplicate |
| Ngắn nhất | `w4uxYDPsjbw` | 653 ký tự |
| Dài nhất | `o9nW0uBqvEo` | 49.645 ký tự, 1.262 segment |
| Code-heavy | `FlGjISF3l78` | Python code signal cao nhất |
| Caption cue và duplicate | `6LOwPhPDwVc` | 6 cue và 6 duplicate |

Sample đạt khi:

1. Silver text ở từng segment bằng Bronze text.
2. Timing bằng Bronze, không làm tròn.
3. Segment count và source index khớp.
4. Source/content hash tính lại hợp lệ.
5. JSON Schema validation pass.
6. Chạy hai lần tạo output byte-identical.
7. Không ghi transcript text vào report.

Chỉ sau khi sample đạt mới được chạy cleaning đủ 38 target payload.

## Sample implementation

Script:

```text
scripts/cleaning/build_silver_sample.py
```

Output generated:

```text
data/silver/mit_60001/samples/transcripts_clean_sample.jsonl
```

Report không chứa transcript text:

```text
reports/07_cleaning/sample_validation.csv
reports/07_cleaning/sample_cross_process_validation.csv
```
