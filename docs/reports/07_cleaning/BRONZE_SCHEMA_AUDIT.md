# Báo cáo audit Bronze transcript schema

## Ngày thực hiện

2026-07-26

## Phạm vi

```text
Course: MIT 6.0001
Term: Fall 2016
Scope version: mit_60001_fall_2016_v1
Target payloads: 38
```

Audit chỉ đọc target manifest và Bronze transcript JSONL. Không thay đổi Bronze,
PostgreSQL hoặc nội dung transcript.

## Payload schema thực tế

Mỗi payload có đủ sáu field:

| Field | Kiểu dữ liệu | Độ phủ |
| --- | --- | ---: |
| `video_id` | string | 38/38 |
| `language_code` | string | 38/38 |
| `language` | string | 38/38 |
| `is_generated` | boolean | 38/38 |
| `segments` | array | 38/38 |
| `fetched_at` | string ISO-8601 | 38/38 |

Không có field top-level ngoài schema trên.

## Segment schema thực tế

Corpus có tổng cộng 12.518 segment. Mỗi segment có đúng ba field:

| Field | Kiểu dữ liệu | Độ phủ |
| --- | --- | ---: |
| `text` | string | 12.518/12.518 |
| `start` | number | 12.518/12.518 |
| `duration` | number | 12.518/12.518 |

Không phát hiện:

- segment rỗng;
- `start` âm hoặc sai kiểu;
- `duration` không dương hoặc sai kiểu;
- segment sai thứ tự thời gian;
- timestamp `fetched_at` không parse được;
- field payload hoặc segment ngoài schema đã biết.

## Language và transcript source

```text
language_code=en: 38
is_generated=False: 38
```

Tên language có hai biến thể:

```text
English - CC: 37
English - CC (English): 1
```

Biến thể thứ hai thuộc video `nykOeWgQcHM`, position 0. Silver contract phải dùng
`language_code=en` làm giá trị chuẩn và giữ `language` như metadata nguồn. Không
được dùng tên language hiển thị để phân nhóm ngôn ngữ.

`is_generated=False` chỉ phản ánh metadata do transcript source trả về. Nó không
chứng minh transcript không có lỗi nhận dạng hoặc lỗi phụ đề.

## Phân bố kích thước

| Chỉ số | Nhỏ nhất | Trung bình | Lớn nhất |
| --- | ---: | ---: | ---: |
| Segment mỗi video | 16 | 329 | 1.262 |
| Transcript length | 653 | 13.243 | 49.645 |

Transcript length được tính bằng cách strip từng segment không rỗng rồi nối bằng
newline, cùng cách loader hiện tại tạo `raw_text` cho PostgreSQL.

Các trường hợp biên:

| Loại | Video ID | Title | Giá trị |
| --- | --- | --- | ---: |
| Ngắn nhất | `w4uxYDPsjbw` | Strings | 653 ký tự |
| Ít segment nhất | `vqn_yk5aFcI` | Class Definition | 16 segment |
| Dài nhất | `o9nW0uBqvEo` | 10. Understanding Program Efficiency, Part 1 | 49.645 ký tự |
| Nhiều segment nhất | `o9nW0uBqvEo` | 10. Understanding Program Efficiency, Part 1 | 1.262 segment |

## Đặc điểm cần xử lý trong cleaning contract

### Segment có newline

```text
Segments có newline: 9.048/12.518
```

Newline xuất hiện phổ biến trong caption text, không phải ngoại lệ hiếm. Không
được xóa toàn bộ newline bằng một quy tắc chưa được kiểm thử vì có thể làm thay đổi
ranh giới dòng của ví dụ code hoặc nội dung trình bày.

### Segment chồng thời gian

```text
Adjacent segment pairs có overlap: 1.450
```

Overlap không được đánh dấu là schema failure vì caption có thể hiển thị nối tiếp
với khoảng thời gian giao nhau. Silver cleaning không được tự sửa `start` hoặc
`duration`. Timing gốc phải được giữ để phục vụ citation.

### Tín hiệu code-heavy

`python_code_signal_count` chỉ là heuristic đếm keyword và toán tử, dùng để chọn
sample review. Nó không phải nhãn nội dung và không được dùng để sửa transcript.

Các ứng viên có tín hiệu cao:

| Video ID | Title | Signal count |
| --- | --- | ---: |
| `FlGjISF3l78` | 9. Python Classes and Inheritance | 210 |
| `0jljZRnHwOI` | 2. Branching and Iteration | 195 |
| `9H6muyZjms0` | 7. Testing, Debugging, Exceptions, and Assertions | 188 |
| `-DP1i2ZU9gk` | 8. Object Oriented Programming | 176 |
| `WPSeyjX1-4s` | 6. Recursion and Dictionaries | 165 |

## Output

```text
scripts/cleaning/audit_target_bronze.py
reports/07_cleaning/bronze_schema_audit.csv
reports/07_cleaning/bronze_payload_profile.csv
reports/07_cleaning/bronze_audit_summary.csv
```

Không CSV nào chứa transcript text hoặc segment text.

## Kết luận

Bronze schema của 38 target payload hợp lệ và đồng nhất về field cùng kiểu dữ liệu.
Milestone tiếp theo có thể thiết kế Silver transcript contract dựa trên schema đã
quan sát, nhưng phải quyết định rõ cách giữ newline và overlapping timing trước
khi viết full cleaning pipeline.
