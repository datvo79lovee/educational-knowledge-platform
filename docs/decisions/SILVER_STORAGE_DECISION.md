# Quyết định nơi lưu Silver transcript

## Trạng thái quyết định

Đã chấp nhận ngày 2026-07-26 cho target corpus MIT 6.0001 v1.

## Bối cảnh

Bronze giữ 38 target payload với 12.518 segment. PostgreSQL hiện lưu một dòng mỗi
video gồm `language`, `raw_text` và `retrieved_at`, nhưng không lưu segment timing,
`is_generated`, source hash hoặc cleaning version.

Chunking và citation cần timing ở cấp segment. Vì vậy không thể dùng riêng
PostgreSQL `transcripts.raw_text` làm nguồn downstream.

## Quyết định

Sử dụng ba lớp với trách nhiệm riêng:

| Lớp | Trách nhiệm |
| --- | --- |
| Bronze JSONL | Payload gốc bất biến và đầy đủ segment |
| PostgreSQL | Transcript text đã load, JOIN video metadata và kiểm tra coverage |
| Silver JSONL | Cleaned segment-rich record dùng cho chunking và citation |

Silver output:

```text
data/silver/mit_60001/transcripts_clean.jsonl
```

Contract:

```text
docs/design/SILVER_TRANSCRIPT_CONTRACT.md
schemas/silver_transcript_v1.schema.json
```

Không ALTER TABLE `transcripts` trong phase Silver v1.

## Lý do

- Bronze đã giữ toàn bộ segment và là source of truth phù hợp để rebuild.
- Silver JSONL giữ cấu trúc nested tự nhiên mà không cần migration database.
- Downstream chunking cần đọc tuần tự toàn corpus, không cần query từng segment bằng
  SQL ở MVP hiện tại.
- Tránh duy trì cùng một mảng segment trong cả PostgreSQL và Silver.
- Output Silver có thể version, hash, validate và rebuild độc lập.
- Không làm tăng rủi ro cho 324 transcript đang có trong PostgreSQL.

## Phương án không chọn

### Thêm JSONB segments vào `transcripts`

Không chọn ở v1 vì:

- sao chép dữ liệu nested đã có trong Bronze và Silver;
- cần migration cùng quy tắc đồng bộ ba bản dữ liệu;
- chưa có truy vấn SQL thực tế cần JSONB segment;
- một thay đổi cleaning có thể buộc cập nhật JSONB cho toàn corpus.

### Tạo bảng `transcript_segments`

Đây là phương án hợp lệ khi sản phẩm cần query segment trực tiếp bằng SQL, nhưng
chưa chọn cho MVP vì:

- tạo ít nhất 12.518 row chỉ cho target hiện tại;
- cần unique constraint, foreign key, migration và loader riêng;
- chunking hiện là batch pipeline, đọc JSONL phù hợp hơn;
- chưa có API hoặc workload chứng minh cần relational segment store.

### Chỉ dùng PostgreSQL `raw_text`

Không chọn vì `raw_text` đã mất timing và ranh giới segment nguồn. Không thể tạo
timestamp citation đáng tin cậy chỉ từ text đã nối.

## Hệ quả

- Cleaning và chunking phải đọc target manifest cùng Bronze/Silver, không lấy toàn
  bộ 324 transcript từ PostgreSQL.
- PostgreSQL không phải source of truth cho segment timing.
- Silver file là generated data trong `.gitignore`; Git chỉ lưu schema, code và
  report không chứa transcript text.
- Mọi Silver record phải có source payload hash, content hash, scope version và
  cleaning version.
- Thay đổi cleaning rule phải tăng `cleaning_version` và rebuild Silver.
- Thay đổi shape record phải tạo `schema_version` mới, không sửa ngầm v1.

## Khi nào xem xét lại

Xem xét bảng relational `transcript_segments` hoặc JSONB khi có ít nhất một nhu
cầu cụ thể:

- API cần query segment theo thời gian trực tiếp trong PostgreSQL;
- nhiều pipeline hoặc người dùng cần cập nhật đồng thời;
- cần incremental update ở cấp segment;
- cần database constraint ở cấp segment;
- JSONL không còn đáp ứng kích thước hoặc vận hành production.

Nếu xem xét lại, phải tạo migration riêng và giữ khả năng rebuild từ Bronze.
