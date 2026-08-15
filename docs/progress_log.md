# Educational Knowledge Platform - Build Log

---

# Ngày 1 - Foundation Setup

## Đã hoàn thành

### 1. Thiết kế kiến trúc hệ thống

File:

```text
docs/architecture.md
```

Mục đích:

Thiết kế kiến trúc tổng thể cho nền tảng tri thức giáo dục theo hướng Data Engineering Pipeline.

Đã triển khai:

* Xác định luồng dữ liệu từ YouTube API đến Vector Database.
* Áp dụng kiến trúc Medallion gồm Bronze, Silver và Gold Layer.
* Xác định PostgreSQL là nơi lưu metadata và quản lý dữ liệu có cấu trúc.
* Xác định các giai đoạn chính: ingestion, processing, embedding và semantic search.

Kết quả:

Hoàn thành kiến trúc tổng thể của dự án:

```text
YouTube API
↓
Bronze Layer
↓
Silver Layer
↓
Gold Layer
↓
Embedding Pipeline
↓
Vector Database
```

---

### 2. Thiết kế mô hình dữ liệu

File:

```text
sql/schema.sql
```

Mục đích:

Thiết kế schema PostgreSQL để lưu trữ metadata video, transcript và chunk phục vụ semantic search.

Đã triển khai:

* Thiết kế bảng `sources` để lưu thông tin nguồn dữ liệu.
* Thiết kế bảng `videos` để lưu metadata video.
* Thiết kế bảng `transcripts` để lưu transcript gốc.
* Thiết kế bảng `chunks` để lưu dữ liệu sau khi chunking.
* Thiết kế quan hệ khóa ngoại giữa video, transcript và chunk.

Kết quả:

Hoàn thành schema database ban đầu với các bảng:

* `sources`
* `videos`
* `transcripts`
* `chunks`

---

### 3. Thiết lập môi trường phát triển

File:

```text
README.md
```

Mục đích:

Chuẩn bị môi trường làm việc để có thể phát triển ingestion pipeline và quản lý dữ liệu.

Đã triển khai:

* Cài đặt PostgreSQL.
* Kết nối PostgreSQL bằng DataGrip.
* Tạo database `educational_knowledge_platform`.
* Khởi tạo cấu trúc thư mục dự án.
* Chuẩn bị Python environment.

Kết quả:

Môi trường phát triển đã sẵn sàng cho giai đoạn ingestion.

---

### 4. Khởi tạo GitHub Repository

File:

```text
.gitignore
```

Mục đích:

Thiết lập quản lý mã nguồn cho dự án.

Đã triển khai:

* Khởi tạo Git repository.
* Kết nối GitHub remote.
* Tạo commit đầu tiên.
* Push source code lên GitHub.

Kết quả:

Dự án đã được quản lý bằng Git và có repository trên GitHub.

---

### 5. Git History

Đã commit:

* `setup project and design architecture`
* `add database schema`

---

# Những điều đã học được

## Medallion Architecture

Đã hiểu:

* Bronze Layer lưu dữ liệu gần với source nhất.
* Silver Layer dùng cho cleaning, deduplication và validation.
* Gold Layer dùng cho dữ liệu đã được tổ chức phục vụ analytics hoặc downstream application.

---

## Database Schema

Đã hiểu:

* `schema.sql` là file mã nguồn SQL dùng để tái tạo cấu trúc database.
* PostgreSQL Schema là đối tượng quản lý namespace bên trong database.
* Thiết kế schema sớm giúp định hình pipeline và quan hệ dữ liệu.

---

## Project Foundation

Đã hiểu:

* Cần thiết kế kiến trúc trước khi code pipeline.
* ERD giúp xác định entity, relationship và ràng buộc dữ liệu.
* Git history giúp theo dõi tiến độ theo từng milestone.

---

# Vấn đề còn tồn tại

Hiện tại:

Dự án mới hoàn thành phần foundation, chưa có ingestion pipeline thực tế.

Nguyên nhân:

Chưa kết nối YouTube Data API và chưa xác định endpoint phù hợp để thu thập dữ liệu từ MIT OpenCourseWare.

Cần thực hiện tiếp:

* Thiết lập YouTube Data API.
* Tìm Channel ID của MIT OpenCourseWare.
* Tìm Uploads Playlist ID.
* Thu thập danh sách video đầu tiên.

---

# Mục tiêu Ngày 2

## Mục tiêu chính

Xây dựng ingestion pipeline đầu tiên để thu thập danh sách video từ MIT OpenCourseWare và lưu vào Bronze Layer.

---

## Bước 1

Kết nối YouTube Data API bằng API Key được quản lý trong `.env`.

---

## Bước 2

Tạo script lấy Channel ID của MIT OpenCourseWare.

---

## Bước 3

Tạo script lấy Uploads Playlist ID từ Channel ID.

---

## Bước 4

Tạo pagination pipeline để đọc toàn bộ video trong Uploads Playlist.

---

## Bước 5

Ghi raw playlist items vào Bronze Layer dưới định dạng JSONL.

---

# Tiêu chí hoàn thành Ngày 2

Thành công nếu đạt được:

* Kết nối thành công YouTube Data API.
* Lấy được Channel ID của MIT OpenCourseWare.
* Lấy được Uploads Playlist ID.
* Thu thập được danh sách video từ channel.
* Tạo được file Bronze raw đầu tiên.

---

# Trạng thái tổng thể dự án

Tiến độ hiện tại:

Phase 1 - Foundation

✅ Hoàn thành

* Architecture Design
* ERD Design
* PostgreSQL Setup
* Database Schema
* GitHub Repository

---

Phase 2 - Ingestion

⬜ YouTube API Integration

⬜ Channel Discovery

⬜ Uploads Playlist Discovery

⬜ Playlist Pagination

⬜ Bronze Ingestion

---

Phase 3 - Processing

⬜ Silver Layer

⬜ Gold Layer

---

Phase 4 - Knowledge Retrieval

⬜ Transcript Processing

⬜ Embedding

⬜ Vector Database

⬜ Semantic Search

---

# Ngày 2 - YouTube Bronze Ingestion

## Đã hoàn thành

### 1. Thiết lập YouTube Data API

File:

```text
.env
test_youtube.py
```

Mục đích:

Kết nối dự án với YouTube Data API để có thể thu thập dữ liệu từ MIT OpenCourseWare.

Đã triển khai:

* Tạo YouTube Data API Key.
* Lưu API Key trong file `.env`.
* Sử dụng `python-dotenv` để đọc biến môi trường.
* Kiểm tra kết nối API bằng script test.

Kết quả:

Kết nối thành công YouTube Data API.

---

### 2. Lấy Channel ID

File:

```text
src/ingestion/get_channel.py
```

Mục đích:

Tìm Channel ID chính xác của MIT OpenCourseWare để làm điểm bắt đầu cho ingestion pipeline.

Đã triển khai:

* Gọi YouTube API để tìm thông tin channel.
* Xác định channel chính thức của MIT OpenCourseWare.
* Trích xuất Channel ID để dùng ở các bước sau.

Kết quả:

Channel ID:

```text
UCEBb1b_L6zDS3xTUrIALZOw
```

---

### 3. Lấy Uploads Playlist

File:

```text
src/ingestion/get_uploads_playlist.py
```

Mục đích:

Tìm playlist chứa toàn bộ video upload của MIT OpenCourseWare.

Đã triển khai:

* Gọi `youtube.channels().list()`.
* Sử dụng `part="contentDetails"`.
* Đọc `relatedPlaylists.uploads`.
* Trích xuất Uploads Playlist ID.

Kết quả:

Uploads Playlist ID:

```text
UUEBb1b_L6zDS3xTUrIALZOw
```

---

### 4. Xây dựng Pagination Pipeline

File:

```text
src/ingestion/fetch_playlist_videos.py
```

Mục đích:

Thu thập toàn bộ playlist items từ Uploads Playlist của MIT OpenCourseWare.

Đã triển khai:

* Gọi `youtube.playlistItems().list()`.
* Sử dụng `part="snippet"`.
* Sử dụng `maxResults=50`.
* Lặp qua toàn bộ dữ liệu bằng `nextPageToken`.
* Gom tất cả playlist items vào collection.

Kết quả:

* Total Records: 8021
* Unique Video IDs: 8021
* Duplicate Video IDs: 0

---

### 5. Xây dựng Bronze Layer đầu tiên

File:

```text
data/bronze/videos_raw.jsonl
```

Mục đích:

Lưu raw playlist items từ YouTube API vào Bronze Layer.

Đã triển khai:

* Ghi mỗi playlist item thành một dòng JSON.
* Sử dụng định dạng JSON Lines.
* Giữ dữ liệu gần với source nhất.
* Chưa thực hiện deduplication, cleaning hoặc validation ở Bronze Layer.

Kết quả:

Tạo thành công file:

```text
data/bronze/videos_raw.jsonl
```

File chứa 8021 raw playlist items.

---

### 6. Git History

Đã commit:

* `feat: lấy Channel ID từ kênh YouTube`
* `feat: lấy Uploads Playlist từ Channel ID`
* `feat: xây dựng pipeline phân trang thu thập video (pagination)`
* `chore: bổ sung gitignore cho data lake và môi trường`
* `docs: cập nhật kế hoạch dự án và tiến độ ngày 2`

---

# Những điều đã học được

## Search API không phù hợp

Đã hiểu:

* `youtube.search().list()` phục vụ bài toán tìm kiếm.
* Search API không phù hợp để ingestion toàn bộ video của một channel.
* Ingestion cần đi theo luồng Channel → Uploads Playlist → Playlist Items.

---

## Pagination

Đã hiểu:

* Một request `playlistItems().list()` trả tối đa 50 records.
* `nextPageToken` dùng để lấy trang tiếp theo.
* Khi `nextPageToken` bằng `None` thì đã đọc hết dữ liệu.
* Tổng số request cần thực hiện khoảng 161 request cho 8021 video.

---

## Bronze Layer

Đã hiểu:

* Bronze Layer nên lưu dữ liệu gần với source nhất.
* Nếu source có duplicate thì Bronze vẫn có thể lưu duplicate.
* Deduplication, validation và data cleaning nên thực hiện ở Silver Layer.
* JSONL phù hợp với dữ liệu lớn vì có thể đọc theo từng dòng.

---

# Vấn đề còn tồn tại

Hiện tại:

`data/bronze/videos_raw.jsonl` chỉ chứa playlist item raw, chưa phải video metadata hoàn chỉnh.

Nguyên nhân:

`playlistItems().list()` không trả về đầy đủ các trường cần cho bảng `videos`, đặc biệt là:

* `duration`
* `view_count`

Cần thực hiện tiếp:

* Đọc `video_id` từ Bronze Layer.
* Gọi `youtube.videos().list()`.
* Thu thập metadata chi tiết cho từng video.
* Lưu kết quả vào Bronze Metadata Layer.

---

# Mục tiêu Ngày 3

## Mục tiêu chính

Thu thập metadata chi tiết cho toàn bộ video.

---

## Bước 1

Tạo file:

```text
src/ingestion/fetch_video_metadata.py
```

---

## Bước 2

Đọc:

```text
data/bronze/videos_raw.jsonl
```

Lấy:

```text
video_id
```

---

## Bước 3

Sử dụng:

```text
youtube.videos().list()
```

Để lấy:

* `video_id`
* `title`
* `description`
* `publish_date`
* `duration`
* `view_count`

---

## Bước 4

Batching:

* Mỗi request xử lý tối đa 50 `video_id`.
* Tổng số batch dự kiến: 161.

---

## Bước 5

Lưu kết quả:

```text
data/bronze/video_metadata_raw.jsonl
```

---

# Tiêu chí hoàn thành Ngày 3

Thành công nếu đạt được:

* Đọc được `video_id` từ Bronze.
* Gọi thành công `videos().list()`.
* Thu thập được `duration`.
* Thu thập được `view_count`.
* Tạo được `video_metadata_raw.jsonl`.
* Chuẩn bị dữ liệu cho bước load PostgreSQL.

---

# Trạng thái tổng thể dự án

Tiến độ hiện tại:

Phase 1 - Foundation

✅ Hoàn thành

* Architecture Design
* ERD Design
* PostgreSQL Setup
* Database Schema
* GitHub Repository

---

Phase 2 - Ingestion

✅ YouTube API Integration

✅ Channel Discovery

✅ Uploads Playlist Discovery

✅ Playlist Pagination

✅ Bronze Playlist Items Ingestion

⬜ Video Metadata Enrichment

⬜ PostgreSQL Loading

---

Phase 3 - Processing

⬜ Silver Layer

⬜ Gold Layer

---

Phase 4 - Knowledge Retrieval

⬜ Transcript Processing

⬜ Embedding

⬜ Vector Database

⬜ Semantic Search

---

# Ngày 3 - Metadata Enrichment Pipeline

## Đã hoàn thành

### 1. Xây dựng Metadata Extraction Pipeline

File:

```text
src/ingestion/fetch_video_metadata.py
```

Mục đích:

Đọc Bronze playlist items và trích xuất `video_id` để chuẩn bị gọi Videos API.

Đã triển khai:

* Đọc dữ liệu từ `data/bronze/videos_raw.jsonl`.
* Trích xuất `video_id` từ `snippet.resourceId.videoId`.
* Kiểm tra số lượng record đầu vào.
* Kiểm tra số lượng `video_id` bị thiếu.

Kết quả:

* Total Records: 8021
* Video IDs: 8021
* Missing Video IDs: 0

---

### 2. Thực hiện Deduplication

File:

```text
src/ingestion/fetch_video_metadata.py
```

Mục đích:

Loại bỏ `video_id` trùng lặp trước khi gọi Metadata API để tránh gọi API thừa.

Đã triển khai:

* Xây dựng hàm `deduplicate_video_ids()`.
* Deduplicate danh sách `video_id` trong memory.
* Giữ nguyên dữ liệu raw ở Bronze Layer.

Kết quả:

* Before Dedup: 8021
* After Dedup: 8021
* Duplicates: 0

---

### 3. Xây dựng Batching Pipeline

File:

```text
src/ingestion/fetch_video_metadata.py
```

Mục đích:

Chia danh sách `video_id` thành các batch để tuân thủ giới hạn của Videos API.

Đã triển khai:

* Xây dựng hàm `chunk_list()`.
* Thiết lập batch size bằng 50.
* Chia 8021 `video_id` thành nhiều batch.
* Xác nhận số lượng video trong batch cuối.

Kết quả:

* Batch Size: 50
* Total Batches: 161
* Videos In Last Batch: 21

---

### 4. Khám phá Videos API

File:

```text
src/ingestion/fetch_video_metadata.py
```

Mục đích:

Kiểm tra khả năng thu thập metadata chi tiết từ YouTube Videos API.

Đã triển khai:

* Gọi `youtube.videos().list()`.
* Sử dụng `part="snippet,contentDetails,statistics"`.
* Kiểm tra các trường dữ liệu trả về từ API.

Kết quả:

Xác nhận có thể thu thập:

* `video_id`
* `title`
* `description`
* `publish_date`
* `duration`
* `view_count`

---

### 5. Xây dựng Metadata Collection Pipeline

File:

```text
src/ingestion/fetch_video_metadata.py
```

Mục đích:

Thu thập metadata chi tiết cho toàn bộ video từ MIT OpenCourseWare.

Đã triển khai:

* Xây dựng hàm `fetch_video_metadata()`.
* Gọi Videos API theo từng batch.
* Thu thập metadata từ `snippet`, `contentDetails` và `statistics`.
* Gom kết quả vào memory trước khi ghi ra file.

Kết quả:

* Total Batches Processed: 161
* Metadata Records Collected: 8021

---

### 6. Xây dựng Bronze Metadata Layer

File:

```text
data/bronze/video_metadata_raw.jsonl
```

Mục đích:

Lưu raw metadata từ Videos API vào Bronze Layer.

Đã triển khai:

* Ghi mỗi video metadata thành một dòng JSON.
* Giữ raw response từ Videos API.
* Chưa thực hiện cleaning.
* Chưa thực hiện validation.
* Chưa map sang schema PostgreSQL.

Kết quả:

* Expected Records: 8021
* Records Written: 8021

---

### 7. Git History

Đã commit:

* `feat: xây dựng pipeline thu thập metadata video`
* `docs: viet log cho ngay 3 va dat nhiem vu cho ngay 4 (20/6/2026)`
* `docs: chỉnh sửa lại cấu trúc log cho 3 ngày và chốt cấu trúc chung cho các ngày còn lại"`
---

# Những điều đã học được

## Playlist Items API không đủ cho Video Schema

Đã hiểu:

* `playlistItems().list()` chỉ trả về playlist item metadata.
* Playlist Items API không trả về `duration`.
* Playlist Items API không trả về `view_count`.
* Cần dùng Videos API để enrich metadata cho bảng `videos`.

---

## Videos API

Đã hiểu:

* `videos().list()` cho phép lấy metadata chi tiết của video.
* `snippet` chứa `title`, `description` và `publishedAt`.
* `contentDetails` chứa `duration`.
* `statistics` chứa `viewCount`.

---

## Batching

Đã hiểu:

* Videos API chỉ nhận tối đa 50 `video_id` mỗi request.
* Cần chia batch trước khi gọi API.
* Batching giúp pipeline tuân thủ API limit và dễ log tiến độ.

---

## Bronze Layer

Đã hiểu:

* Bronze Layer có thể gồm nhiều tập dữ liệu raw khác nhau.
* `videos_raw.jsonl` là raw response từ Playlist Items API.
* `video_metadata_raw.jsonl` là raw response từ Videos API.
* Cả hai đều thuộc Bronze Layer.

---

# Vấn đề còn tồn tại

Hiện tại:

`data/bronze/video_metadata_raw.jsonl` vẫn là raw JSON response từ YouTube Videos API.

Nguyên nhân:

Bronze Layer chỉ chịu trách nhiệm lưu dữ liệu gần với source nhất, chưa thực hiện schema mapping hoặc data quality check.

Cần thực hiện tiếp:

* Kiểm tra chất lượng dữ liệu.
* Kiểm tra missing fields.
* Thiết kế mapping từ raw metadata sang bảng `videos`.
* Chuẩn bị PostgreSQL Loading Pipeline.

---

# Mục tiêu Ngày 4

## Mục tiêu chính

Kiểm tra chất lượng dữ liệu và chuẩn bị load PostgreSQL.

---

## Bước 1

Tạo file:

```text
src/quality/check_video_metadata.py
```

---

## Bước 2

Đọc:

```text
data/bronze/video_metadata_raw.jsonl
```

---

## Bước 3

Kiểm tra:

* Missing `title`
* Missing `description`
* Missing `publish_date`
* Missing `duration`
* Missing `view_count`

---

## Bước 4

Thiết kế mapping:

```text
Video Metadata Raw
↓
Videos Table
```

Mapping cần có:

* `id` → `video_id`
* `snippet.title` → `title`
* `snippet.description` → `description`
* `snippet.publishedAt` → `publish_date`
* `contentDetails.duration` → `duration_seconds`
* `statistics.viewCount` → `view_count`

---

## Bước 5

Chuẩn bị PostgreSQL Loading Pipeline.

---

# Tiêu chí hoàn thành Ngày 4

Thành công nếu đạt được:

* Hoàn thành Data Quality Check.
* Xác nhận dữ liệu đủ điều kiện load DB.
* Hoàn thành mapping sang schema `videos`.
* Sẵn sàng triển khai PostgreSQL Loading.

---

# Trạng thái tổng thể dự án

Tiến độ hiện tại:

Phase 1 - Foundation

✅ Hoàn thành

* Architecture Design
* ERD Design
* PostgreSQL Setup
* Database Schema
* GitHub Repository

---

Phase 2 - Ingestion

✅ YouTube API Integration

✅ Channel Discovery

✅ Uploads Playlist Discovery

✅ Playlist Pagination

✅ Bronze Playlist Items Ingestion

✅ Video Metadata Enrichment

🟡 Data Quality Check

⬜ PostgreSQL Loading

---

Phase 3 - Processing

⬜ Silver Layer

⬜ Gold Layer

---

Phase 4 - Knowledge Retrieval

⬜ Transcript Processing

⬜ Embedding

⬜ Vector Database

⬜ Semantic Search


---

# Ngày 4 - Data Quality, Transformation và Silver Layer

## Đã hoàn thành

### 1. Data Quality Check cho Video Metadata

File:

```text
src/quality/check_video_metadata.py
```

Mục đích:

Đánh giá chất lượng dữ liệu raw từ YouTube Videos API trước khi chuyển sang bước transform và load vào PostgreSQL.

Đã triển khai:

* Đọc dữ liệu từ `data/bronze/video_metadata_raw.jsonl`.
* Kiểm tra tổng số record metadata đã ingest.
* Kiểm tra duplicate theo `video_id`.
* Kiểm tra các object bắt buộc trong API response gồm `snippet`, `contentDetails` và `statistics`.
* Kiểm tra các field cần map sang bảng `videos` gồm `title`, `description`, `publishedAt`, `duration` và `viewCount`.

Kết quả:

```text
Total Records: 8021
Duplicate Video IDs: 0

Missing Snippet: 0
Missing ContentDetails: 0
Missing Statistics: 0

Missing Title: 0
Missing Description: 2
Missing PublishedAt: 0
Missing Duration: 0
Missing ViewCount: 0
```

Dữ liệu metadata đạt chất lượng tốt, không có duplicate và đủ điều kiện để tiếp tục chuyển đổi sang Silver Layer. Hai record thiếu `description` không ảnh hưởng đến schema vì `description` là field có thể nullable.

---

### 2. Cross Validation giữa Playlist Bronze và Metadata Bronze

File:

```text
src/quality/check_cross_validation.py
```

Mục đích:

Đảm bảo toàn bộ video thu thập từ playlist ingestion đều có metadata tương ứng sau bước enrichment bằng YouTube Videos API.

Đã triển khai:

* Đọc danh sách video từ `data/bronze/videos_raw.jsonl`.
* Đọc danh sách metadata từ `data/bronze/video_metadata_raw.jsonl`.
* Trích xuất `video_id` từ playlist layer.
* Trích xuất `id` từ metadata layer.
* So sánh hai tập ID để phát hiện video bị thiếu metadata.

Kết quả:

```text
Playlist Video Count: 8021
Metadata Video Count: 8021
Missing Metadata Videos: 0
```

Không có video nào bị mất trong quá trình metadata enrichment. Bronze Layer hiện có đầy đủ dữ liệu cần thiết để transform sang schema nghiệp vụ.

---

### 3. Xây dựng Transformation Pipeline sang Silver Layer

File:

```text
src/processing/transform_video_metadata.py
```

Mục đích:

Chuẩn hóa raw metadata từ Bronze Layer thành dataset sạch, có cấu trúc phù hợp với schema bảng `videos` trong PostgreSQL.

Đã triển khai:

* Xây dựng `load_jsonl()` để đọc raw JSONL từ Bronze Layer.
* Xây dựng `parse_publish_date()` để chuyển `publishedAt` từ ISO datetime sang date.
* Xây dựng `parse_view_count()` để chuyển `viewCount` từ string sang integer.
* Xây dựng `parse_duration_to_seconds()` để chuyển ISO 8601 duration sang tổng số giây.
* Xây dựng rule xử lý ngoại lệ `P0D` bằng cách trả về `NULL` thay vì loại bỏ record.
* Xây dựng `transform_video_record()` để map raw response sang schema `videos`.
* Xây dựng `write_jsonl()` để ghi dữ liệu clean ra Silver Layer.

Kết quả:

```text
8021 raw records
↓
8021 clean records
```

Mapping chính:

```text
id → video_id
source_id → source_id
snippet.title → title
snippet.description → description
snippet.publishedAt → publish_date
contentDetails.duration → duration_seconds
statistics.viewCount → view_count
```

Transformation Pipeline đã tạo được dataset Silver ổn định, giữ nguyên số lượng record và chuẩn hóa các field quan trọng phục vụ database loading.

---

### 4. Phát hiện và xử lý dữ liệu ngoại lệ `P0D`

File:

```text
src/processing/transform_video_metadata.py
```

Mục đích:

Xử lý đúng trường hợp YouTube API trả về duration chưa hoàn chỉnh cho livestream hoặc video chưa finalize metadata tại thời điểm ingest.

Đã triển khai:

* Phát hiện một record có `contentDetails.duration = P0D`.
* Điều tra video `pw-x4EgPU_U` với tiêu đề `Celebrating OCW's "NextGen" Platform with NPR's Anya Kamenetz`.
* Xác định đây là trường hợp livestream, metadata tại thời điểm ingest chưa có duration thực tế.
* Quyết định không hard-code duration và không loại bỏ record.
* Map `P0D` thành `duration_seconds = NULL`.

Kết quả:

Pipeline giữ được tính trung thực của dữ liệu theo thời điểm ingest, đồng thời vẫn đảm bảo record có thể load vào PostgreSQL vì `duration_seconds` được thiết kế nullable.

---

### 5. Tạo Silver Dataset cho bảng `videos`

File:

```text
data/silver/videos_clean.jsonl
```

Mục đích:

Lưu dataset đã chuẩn hóa để làm input trực tiếp cho PostgreSQL Loading Pipeline.

Đã triển khai:

* Ghi mỗi clean video record thành một dòng JSON.
* Giữ các field đúng theo schema nghiệp vụ của bảng `videos`.
* Chuẩn hóa `publish_date`, `duration_seconds` và `view_count`.
* Gán `source_id = 1` cho nguồn MIT OpenCourseWare hiện tại.

Kết quả:

```text
Silver Records: 8021
```

Record mẫu:

```json
{
  "video_id": "oz1iDMr5INo",
  "source_id": 1,
  "title": "...",
  "description": "...",
  "publish_date": "2026-06-16",
  "duration_seconds": 240,
  "view_count": 7437
}
```

Silver dataset đã sẵn sàng để load vào PostgreSQL ở ngày tiếp theo.

---

### 6. Thiết kế PostgreSQL Loading Plan

File:

```text
docs/postgresql_loading_plan.md
```

Mục đích:

Thiết kế trước chiến lược load dữ liệu từ Silver Layer vào bảng `videos` để giảm rủi ro khi triển khai pipeline database.

Đã triển khai:

* Xác định input là `data/silver/videos_clean.jsonl`.
* Mô tả schema đích của bảng `videos`.
* Thiết kế mapping giữa Silver fields và PostgreSQL columns.
* Định nghĩa data quality assumptions trước khi load.
* Thiết kế loading strategy theo từng bước.
* Thiết kế duplicate handling bằng `ON CONFLICT (video_id) DO NOTHING`.
* Chuẩn bị validation queries sau khi load.

Kết quả:

Đã có tài liệu kỹ thuật đủ rõ để triển khai `src/database/load_videos.py` trong ngày 5, bao gồm strategy insert, xử lý idempotency và tiêu chí validation sau load.

---

### 7. Git History

Đã commit:

* `feat: kiểm tra video metadata đủ đáp ứng điều kiện để sang Transform`
* `feat: xây dựng pipeline kiểm tra giữa playlist và metadata ở bronze`
* `feat: xây dựng pipeline chuyển đổi metadata sang silver layer`
* `docs: tài liệu thiết kế PostgreSQL Loading Plan.`
* `docs: doc ngày 4 và kế hoạch cho ngày 5.`


---

# Những điều đã học được

## Data Quality phải đứng trước Database Loading

Đã hiểu:

* Không nên load dữ liệu raw trực tiếp vào PostgreSQL nếu chưa kiểm tra chất lượng.
* Cần xác nhận record count, duplicate và missing fields trước khi transform.
* Data Quality Check giúp phát hiện sớm vấn đề ở Bronze Layer thay vì để lỗi xuất hiện ở database.
* Một field nullable như `description` có thể thiếu mà không làm pipeline thất bại nếu schema đã thiết kế phù hợp.

---

## Cross Validation giúp bảo vệ tính đầy đủ của pipeline

Đã hiểu:

* Một pipeline enrichment có thể ghi đủ số dòng nhưng vẫn cần đối chiếu ID giữa các layer.
* Playlist Bronze và Metadata Bronze là hai dataset raw khác nhau nhưng phải khớp về `video_id`.
* So sánh bằng set giúp phát hiện nhanh video bị thiếu metadata.
* Cross validation là bước quan trọng trước khi chuyển từ Bronze sang Silver.

---

## YouTube Metadata có thể thay đổi theo thời gian

Đã hiểu:

* YouTube API có thể trả về metadata tạm thời cho livestream hoặc video chưa finalize.
* `P0D` không nhất thiết là dữ liệu sai, mà có thể là trạng thái dữ liệu tại thời điểm ingest.
* Không nên hard-code giá trị duration dựa trên quan sát thủ công sau này.
* Pipeline nên giữ tính reproducible bằng cách xử lý ngoại lệ theo rule rõ ràng.

---

## Silver Layer là lớp chuẩn hóa theo business schema

Đã hiểu:

* Bronze Layer lưu raw API response gần với source nhất.
* Silver Layer chuyển raw response thành schema có thể dùng cho database và downstream processing.
* Transformation cần chuẩn hóa cả tên field, kiểu dữ liệu và nullable rules.
* Silver dataset phải đủ ổn định để trở thành input cho PostgreSQL Loading Pipeline.

---

# Vấn đề còn tồn tại

Hiện tại:

Dữ liệu đã được chuẩn hóa sang Silver Layer nhưng chưa được load vào PostgreSQL.

Nguyên nhân:

Ngày 4 tập trung vào Data Quality, Cross Validation, Transformation và thiết kế loading plan. Phần database loading cần được triển khai riêng để kiểm soát kết nối PostgreSQL, transaction, conflict handling và validation sau load.

Cần thực hiện tiếp:

* Tạo pipeline load dữ liệu từ `data/silver/videos_clean.jsonl`.
* Kết nối PostgreSQL bằng cấu hình hiện có.
* Insert dữ liệu vào bảng `videos`.
* Triển khai `ON CONFLICT (video_id) DO NOTHING` để pipeline chạy lại an toàn.
* Chạy validation query để xác nhận số record và duplicate trong PostgreSQL.

---

# Mục tiêu Ngày 5

## Mục tiêu chính

Load Silver Dataset vào PostgreSQL và hoàn thành bước Database Integration đầu tiên cho bảng `videos`.

---

## Bước 1

Review tài liệu:

```text
docs/postgresql_loading_plan.md
```

Xác nhận lại input file, schema đích, mapping field, conflict handling và validation queries.

---

## Bước 2

Tạo file:

```text
src/database/load_videos.py
```

Pipeline cần có các function chính:

* `load_jsonl()`
* `get_connection()`
* `insert_video()`
* `load_videos()`
* `main()`

---

## Bước 3

Đọc dữ liệu từ:

```text
data/silver/videos_clean.jsonl
```

Kiểm tra nhanh:

* Tổng số record phải là `8021`.
* Field bắt buộc `video_id`, `source_id` và `title` không được thiếu.
* `duration_seconds` có thể `NULL`.

---

## Bước 4

Kết nối PostgreSQL bằng cấu hình dự án.

Kiểm tra:

* Database server đang chạy.
* Bảng `videos` đã tồn tại.
* Bảng `sources` đã có `source_id = 1` cho MIT OpenCourseWare.

---

## Bước 5

Insert dữ liệu vào bảng:

```sql
videos
```

Các column cần load:

* `video_id`
* `source_id`
* `title`
* `description`
* `publish_date`
* `duration_seconds`
* `view_count`

---

## Bước 6

Triển khai idempotent loading:

```sql
ON CONFLICT (video_id)
DO NOTHING
```

Mục tiêu là pipeline có thể chạy lại nhiều lần mà không sinh duplicate.

---

## Bước 7

Validation sau khi load:

```sql
SELECT COUNT(*)
FROM videos;
```

Kỳ vọng:

```text
8021
```

Kiểm tra duplicate:

```sql
SELECT video_id, COUNT(*)
FROM videos
GROUP BY video_id
HAVING COUNT(*) > 1;
```

Kỳ vọng:

```text
0 rows
```

---

# Tiêu chí hoàn thành Ngày 5

Thành công nếu đạt được:

* Load thành công `8021` videos từ Silver Layer vào PostgreSQL.
* Không có duplicate `video_id` trong bảng `videos`.
* Pipeline có thể chạy lại mà không tạo dữ liệu trùng.
* PostgreSQL phản ánh đầy đủ dữ liệu trong `data/silver/videos_clean.jsonl`.
* Hoàn thành Database Integration đầu tiên của dự án.

---

# Trạng thái tổng thể dự án

Tiến độ hiện tại:

Phase 1 - Foundation

✅ Hoàn thành

* Architecture Design
* ERD Design
* PostgreSQL Setup
* Database Schema
* GitHub Repository

---

Phase 2 - Ingestion

✅ YouTube API Integration

✅ Channel Discovery

✅ Uploads Playlist Discovery

✅ Playlist Pagination

✅ Bronze Playlist Items Ingestion

✅ Video Metadata Enrichment

✅ Data Quality Check

✅ Cross Validation

⬜ PostgreSQL Loading

---

Phase 3 - Processing

✅ Silver Layer

🟡 Gold Layer

⬜ Transcript Processing

---

Phase 4 - Knowledge Retrieval

⬜ Embedding Pipeline

⬜ Vector Database

⬜ Semantic Search
--- 
# Ngày 5 - Database Integration

## Đã hoàn thành

### 1. Thiết lập kết nối PostgreSQL

File:

```text
src/database/connection.py
```

Mục đích:

Xây dựng module kết nối PostgreSQL dùng chung cho toàn bộ tầng Database Integration.

Đã triển khai:

* Tạo hàm `get_connection()`.
* Cấu hình kết nối PostgreSQL thông qua file `.env`.
* Kiểm thử kết nối từ Python tới PostgreSQL.

Kết quả:

* Kết nối PostgreSQL thành công.
* Các module database có thể tái sử dụng chung một cơ chế kết nối.

---

### 2. Xây dựng Source Loading Pipeline

File:

```text
src/database/load_sources.py
```

Mục đích:

Đảm bảo dữ liệu nguồn tồn tại trong bảng `sources` trước khi nạp dữ liệu video.

Đã triển khai:

* Thiết kế seed data cho MIT OpenCourseWare.
* Xây dựng hàm validate dữ liệu nguồn.
* Triển khai insert vào bảng `sources`.
* Sử dụng:

```sql
ON CONFLICT (channel_id)
DO NOTHING
```

để hỗ trợ chạy lại pipeline nhiều lần.

Kết quả:

* Nạp thành công source MIT OpenCourseWare.
* Bảng `sources` sẵn sàng phục vụ Foreign Key của bảng `videos`.

---

### 3. Xây dựng Video Loading Pipeline

File:

```text
src/database/load_videos.py
```

Mục đích:

Nạp dữ liệu từ Silver Layer vào PostgreSQL.

Đã triển khai:

* Đọc dữ liệu từ:

```text
data/silver/videos_clean.jsonl
```

* Tách riêng logic đọc file JSONL và logic insert database.
* Kiểm tra tính hợp lệ của từng record.
* Mapping dữ liệu sang schema bảng `videos`.
* Triển khai:

```sql
ON CONFLICT (video_id)
DO NOTHING
```

để pipeline có thể chạy lại nhiều lần mà không sinh duplicate.

Kết quả:

```text
Loaded 8021 records
```

```text
Inserted Records: 8021
Skipped Records: 0
Invalid Records: 0
```

Toàn bộ Silver Dataset đã được load vào PostgreSQL.

---

### 4. Điều tra và xử lý lỗi Foreign Key

Mục đích:

Khắc phục lỗi phát sinh trong quá trình load video.

Đã triển khai:

* Điều tra lỗi:

```text
insert or update on table "videos"
violates foreign key constraint
```

* Phân tích quan hệ:

```text
sources
    ↓
videos
```

* Xác định nguyên nhân là bảng `sources` chưa có dữ liệu.
* Thiết kế lại thứ tự pipeline:

```text
load_sources.py
        ↓
load_videos.py
        ↓
load_transcripts.py
        ↓
load_chunks.py
```

Kết quả:

* Load video thành công.
* Đảm bảo tính toàn vẹn dữ liệu theo Foreign Key Constraint.

---

### 5. Xây dựng Video Validation Pipeline

File:

```text
src/database/validate_video.py
```

Mục đích:

Kiểm tra chất lượng dữ liệu sau khi load vào PostgreSQL.

Đã triển khai:

* Kiểm tra tổng số records.
* Kiểm tra duplicate video_id.
* Kiểm tra missing title.
* Kiểm tra missing publish_date.
* Kiểm tra missing duration.
* Kiểm tra Foreign Key Integrity.
* Thống kê duration.
* Thống kê view count.

Kết quả:

```text
===== RECORD COUNT =====
Total Records: 8021

===== DUPLICATE CHECK =====
PASS - No duplicate video_id found

===== MISSING TITLE =====
Missing Titles: 0

===== MISSING PUBLISH DATE =====
Missing Publish Dates: 0

===== MISSING DURATION =====
Missing Duration: 1

===== FOREIGN KEY CHECK =====
PASS - All videos have valid sources

===== DURATION STATISTICS =====
Min Duration: 3
Max Duration: 62937
Avg Duration: 2435.26

===== VIEW COUNT STATISTICS =====
Min Views: 0
Max Views: 22477641
Avg Views: 66989.09

===== VALIDATION COMPLETED =====
```

---

### 6. Điều tra dữ liệu ngoại lệ sau khi load

Mục đích:

Xác minh các giá trị bất thường trong dataset.

Đã triển khai:

* Điều tra record có:

```text
duration_seconds = NULL
```

* Điều tra record có:

```text
view_count = 0
```

* Truy vết tới video:

```text
Celebrating OCW's "NextGen" Platform with NPR's Anya Kamenetz
```

* Đối chiếu với dữ liệu Bronze Layer và kết quả điều tra trước đó.

Kết quả:

* Xác nhận đây là livestream metadata anomaly.
* Không phải lỗi transform.
* Không chỉnh sửa dữ liệu.
* Giữ nguyên record để phản ánh trạng thái thực tế tại thời điểm ingest.

---

### 7. Git History

Đã commit:

* feat: thiết lập kết nối PostgreSQL cho pipeline
* feat: pipeline nạp dữ liệu nguồn vào bảng sources
* feat: pipeline load dữ liệu nguồn vào bảng sources
* feat: kiểm tra validate sau khi load video
* docs: doc ngày 5 và kế hoạch ngày 6


---

# Những điều đã học được

## Database Loading phải tuân thủ thứ tự phụ thuộc

Đã hiểu:

* Foreign Key quyết định thứ tự load dữ liệu.
* Không thể load videos trước khi sources tồn tại.
* Cần thiết kế dependency giữa các pipeline database.

---

## Data Validation không chỉ là đếm số lượng record

Đã hiểu:

* Cần kiểm tra duplicate.
* Cần kiểm tra missing values.
* Cần kiểm tra Foreign Key Integrity.
* Cần kiểm tra phân bố dữ liệu bằng statistics.

---

## Data Anomaly không đồng nghĩa với Data Error

Đã hiểu:

* Giá trị bất thường cần được điều tra trước khi xử lý.
* Dữ liệu livestream có thể thay đổi theo thời gian.
* Một số anomaly phản ánh thực tế nghiệp vụ thay vì lỗi hệ thống.

---

## Merge Commit và Git History

Đã hiểu:

* Merge commit xuất hiện khi local branch và remote branch khác lịch sử.
* `git pull` mặc định sử dụng merge strategy.
* Có thể sử dụng:

```bash
git pull --rebase origin main
```

để giữ lịch sử commit gọn hơn.

---

# Vấn đề còn tồn tại

Hiện tại:

Pipeline transcript chưa được triển khai.

Nguyên nhân:

* Chưa xây dựng module thu thập transcript.
* Chưa có Bronze Layer cho transcript.
* Chưa có quality check cho transcript.

Cần thực hiện tiếp:

* Nghiên cứu thư viện transcript phù hợp.
* Thiết kế transcript schema.
* Xây dựng transcript ingestion pipeline.
* Kiểm thử transcript trên một tập video nhỏ trước khi mở rộng toàn bộ dataset.

---

# Mục tiêu Ngày 6

## Mục tiêu chính

Khởi động Transcript Pipeline và xác định chiến lược thu thập transcript cho toàn bộ dataset.

---

## Bước 1

Tạo:

```text
src/ingestion/fetch_transcripts.py
```

---

## Bước 2

Thử nghiệm lấy transcript của một video đơn lẻ.

---

## Bước 3

Phân tích cấu trúc dữ liệu transcript trả về.

---

## Bước 4

Thiết kế Bronze Transcript Schema.

Ví dụ:

```text
data/bronze/transcripts_raw.jsonl
```

---

## Bước 5

Thu transcript thử nghiệm cho khoảng:

```text
50 - 100 videos
```

---

## Bước 6

Đánh giá tỷ lệ video có transcript và không có transcript.

---

# Tiêu chí hoàn thành Ngày 6

Thành công nếu đạt được:

* Xây dựng được Transcript Ingestion POC.
* Thu transcript thành công cho tập video mẫu.
* Xác định được cấu trúc Bronze Transcript Layer.
* Hiểu rõ các trường dữ liệu transcript.
* Có cơ sở để triển khai Transcript Quality Check trong ngày tiếp theo.

---

# Trạng thái tổng thể dự án

Tiến độ hiện tại:

Phase 1 - Foundation

✅ Hoàn thành

* Architecture Design
* ERD Design
* PostgreSQL Setup
* Database Schema
* GitHub Repository

---

Phase 2 - Ingestion

✅ YouTube API Integration

✅ Channel Discovery

✅ Uploads Playlist Discovery

✅ Playlist Pagination

✅ Bronze Playlist Items Ingestion

✅ Video Metadata Enrichment

✅ Data Quality Check

✅ Cross Validation

✅ PostgreSQL Loading

---

Phase 3 - Processing

✅ Silver Layer

🟡 Gold Layer

⬜ Transcript Processing

---

Phase 4 - Knowledge Retrieval

⬜ Embedding Pipeline

⬜ Vector Database

⬜ Semantic Search
---
# Ngày 6 - Transcript Collection Pipeline

## Đã hoàn thành

### 1. Nghiên cứu YouTube Transcript API

File:

```text
src/ingestion/fetch_transcripts.py
```

Mục đích:

Đánh giá khả năng thu thập transcript từ YouTube để phục vụ Knowledge Processing Pipeline.

Đã triển khai:

* Nghiên cứu thư viện `youtube-transcript-api`.
* Thử nghiệm lấy transcript của một video đơn lẻ.
* Phân tích cấu trúc dữ liệu trả về.
* Xác định metadata có thể khai thác.

Kết quả:

* API hoạt động ổn định với video của MIT OpenCourseWare.
* Transcript trả về gồm:

  * language
  * language_code
  * is_generated
  * segments
* Mỗi segment bao gồm:

  * text
  * start
  * duration
* Xác nhận phần lớn transcript của MIT là human-created caption, phù hợp cho NLP, Chunking và RAG.

---

### 2. Thiết kế Bronze Transcript Schema

Mục đích:

Thiết kế định dạng lưu trữ transcript tại Bronze Layer nhằm giữ nguyên dữ liệu gốc từ YouTube.

Đã triển khai:

Thiết kế schema gồm:

```text
video_id
language
language_code
is_generated
segments
```

Trong đó:

* `segments` giữ nguyên toàn bộ transcript theo từng đoạn.
* Mỗi đoạn gồm:

  * text
  * start
  * duration

Kết quả:

* Bronze Transcript Layer phản ánh đầy đủ dữ liệu gốc từ YouTube.
* Sẵn sàng cho bước Cleaning và Chunking.

---

### 3. Xây dựng Transcript Fetch Module

File:

```text
src/ingestion/fetch_transcripts.py
```

Mục đích:

Xây dựng module thu thập transcript có thể tái sử dụng cho toàn bộ pipeline.

Đã triển khai:

* Xây dựng hàm lấy transcript cho một video.
* Xây dựng hàm xử lý theo batch.
* Chuẩn hóa dữ liệu trả về.
* Bổ sung Exception Handling cho các trường hợp:

  * Không có transcript.
  * Không đúng ngôn ngữ.
  * IP Block.
  * Các lỗi phát sinh khác.

Kết quả:

* Module có thể tái sử dụng trong Transcript Pipeline.
* Đảm bảo pipeline không dừng khi gặp lỗi của một video đơn lẻ.

---

### 4. Kiểm thử Transcript Pipeline

File:

```text
src/test/
```

Mục đích:

Đánh giá khả năng hoạt động của Transcript API trước khi chạy trên toàn bộ dataset.

Đã triển khai:

* Kiểm thử một video đơn lẻ.
* Kiểm thử batch 5 video.
* Kiểm thử coverage trên 50 video.

Kết quả:

```text
Videos Tested : 50
Success       : 48
Failed        : 2
Success Rate  : 96%
```

Điều tra các trường hợp thất bại:

* Một video chỉ có transcript tiếng Đức.
* Một số video phát sinh giới hạn từ YouTube Transcript API.

---

### 5. Xây dựng Bronze Transcript Loading Pipeline

File:

```text
src/database/load_transcripts.py
```

Mục đích:

Thu thập transcript từ PostgreSQL và lưu trực tiếp xuống Bronze Layer.

Đã triển khai:

* Đọc danh sách `video_id` từ bảng `videos`.
* Thu transcript từng video.
* Ghi trực tiếp vào:

```text
data/bronze/transcripts_raw.jsonl
```

* Ghi theo từng record ngay sau khi thu thành công.

Kết quả:

* Transcript được lưu liên tục trong quá trình chạy.
* Không mất dữ liệu nếu pipeline dừng giữa chừng.

---

### 6. Xây dựng Resume & Checkpoint Mechanism

Mục đích:

Cho phép pipeline tiếp tục từ điểm dừng thay vì chạy lại từ đầu.

Đã triển khai:

* Đọc các `video_id` đã xử lý từ Bronze Layer.
* Skip các transcript đã tồn tại.
* Chỉ xử lý các video chưa được thu.

Kết quả:

* Pipeline hỗ trợ Resume.
* Có thể chạy nhiều phiên liên tiếp mà không sinh dữ liệu trùng lặp.

---

### 7. Xây dựng Runtime Control & Fault Tolerance

Mục đích:

Tăng khả năng vận hành pipeline trên tập dữ liệu lớn.

Đã triển khai:

* Giới hạn thời gian chạy bằng tham số:

```text
--max-runtime-minutes
```

* Thêm Random Delay giữa các request:

```text
--min-delay
--max-delay
```

* Phát hiện và xử lý:

```text
RequestBlocked / IPBlocked
```

* Dừng pipeline an toàn khi gặp IP Block.

Kết quả:

Pipeline có khả năng:

* Resume.
* Checkpoint.
* Fault Tolerance.
* Graceful Stop.
* Runtime Control.

---

### 8. Thu thập Transcript Dataset

Mục đích:

Đánh giá khả năng thu transcript trên tập dữ liệu thực tế.

Kết quả hiện tại:

```text
Total Collected : 290 transcripts
```

Pipeline tự động:

* Skip transcript đã có.
* Thu transcript mới.
* Dừng khi:

  * Đạt Runtime giới hạn.
  * Hoặc gặp IP Block.

Đánh giá:

290 transcript là tập dữ liệu đủ lớn để triển khai các bước tiếp theo gồm:

* Transcript Cleaning.
* Chunking.
* Embedding.
* Semantic Search.

---

### 9. Git History

Đã commit:

* feat: bổ sung thư viện youtube-transcript-api
* feat: xây dựng module thu thập transcript từ YouTube
* feat: xây dựng pipeline thu thập transcript và lưu Bronze Layer
* feat: bổ sung kiểm thử và kiểm tra chất lượng transcript
* docs: doc ngày 6 và kế hoạch ngày 7
---

# Những điều đã học được

## Transcript Pipeline cần hỗ trợ Resume

Đã hiểu:

* Pipeline thu thập dữ liệu lớn không nên chạy lại từ đầu.
* Checkpoint giúp tiết kiệm thời gian và tránh dữ liệu trùng lặp.
* Resume là cơ chế quan trọng của Data Pipeline.

---

## API bên thứ ba luôn có giới hạn

Đã hiểu:

* YouTube Transcript API có thể giới hạn theo IP.
* Cần thiết kế Fault Tolerance thay vì giả định API luôn khả dụng.
* Runtime Control và Graceful Stop giúp pipeline vận hành ổn định hơn.

---

## Bronze Layer nên lưu dữ liệu gốc

Đã hiểu:

* Bronze chỉ lưu dữ liệu nguyên bản.
* Cleaning và Transformation sẽ được thực hiện ở các tầng sau.
* Giữ nguyên transcript gốc giúp dễ dàng truy vết và tái xử lý.

---

## Quy mô dữ liệu cần phù hợp mục tiêu dự án

Đã hiểu:

* Không cần thu toàn bộ transcript để chứng minh Semantic Search.
* Một tập transcript đủ lớn có thể xác thực toàn bộ pipeline downstream.
* Cần cân bằng giữa quy mô dữ liệu và giá trị kỹ thuật của dự án.

---

# Vấn đề còn tồn tại

Hiện tại:

* Một số video không có transcript tiếng Anh.
* YouTube áp dụng IP Rate Limiting khi chạy trong thời gian dài.
* Chưa triển khai Transcript Cleaning và Chunking Pipeline.

---

# Mục tiêu Ngày 7

## Mục tiêu chính

Khởi động Knowledge Processing Pipeline bằng cách xây dựng Transcript Cleaning và Chunking Pipeline.

---

## Bước 1

Thiết kế chiến lược làm sạch transcript.

---

## Bước 2

Xây dựng Transcript Cleaning Pipeline.

---

## Bước 3

Thiết kế thuật toán Chunking theo token hoặc số ký tự.

---

## Bước 4

Xây dựng Chunk Generation Pipeline.

---

## Bước 5

Thiết kế Bronze → Silver Transcript Transformation.

---

## Bước 6

Kiểm thử chất lượng chunk và chuẩn bị cho Embedding Pipeline.

---

# Tiêu chí hoàn thành Ngày 7

Thành công nếu đạt được:

* Hoàn thành Transcript Cleaning Pipeline.
* Hoàn thành Chunk Generation Pipeline.
* Sinh được Chunk Dataset phục vụ Embedding.
* Xác định chiến lược Chunking tối ưu cho Semantic Search.

---

# Trạng thái tổng thể dự án

Tiến độ hiện tại:

Phase 1 - Foundation

✅ Hoàn thành

* Kiến trúc hệ thống
* ERD
* PostgreSQL Schema
* Thiết kế Medallion Architecture

---

Phase 2 - Ingestion

✅ Hoàn thành

* Channel Discovery
* Uploads Playlist Discovery
* Playlist Video Collection
* Metadata Enrichment

---

Phase 3 - Processing

✅ Hoàn thành

* Data Quality Validation
* Cross Validation
* Video Transformation
* Silver Layer Generation

---

Phase 4 - Database Integration

✅ Hoàn thành

* PostgreSQL Connection
* Source Loading
* Video Loading
* Database Validation

---

Phase 5 - Knowledge Processing

🟨 Đang thực hiện

* ✅ Transcript Collection
* ⬜ Transcript Cleaning
* ⬜ Chunking

---

Phase 6 - Knowledge Retrieval

⬜ Chưa bắt đầu

* Embedding Pipeline
* Vector Database
* Semantic Search

---

# Ngày 7 - Data Foundation Audit và PostgreSQL Transcript Loading

## Thay đổi so với kế hoạch ban đầu

Kế hoạch trước đó dự kiến bắt đầu Transcript Cleaning và Chunking. Kế hoạch này
được tạm dừng vì phạm vi của 290 transcript chưa được xác định và dữ liệu
transcript chưa được nạp vào PostgreSQL.

Quyết định trong ngày:

* Không tiếp tục chunking khi data foundation chưa được audit.
* Không crawl lại toàn bộ channel.
* Kiểm tra, nạp và xác minh 290 transcript hiện có trước.
* Phân tích corpus và khôi phục playlist trước khi mở rộng dữ liệu.

---

## Đã hoàn thành

### 1. Ghi nhận trạng thái dữ liệu hiện tại

File:

```text
docs/status/CURRENT_STATUS.md
```

Mục đích:

Phân biệt rõ dữ liệu đã có trong Bronze JSONL, dữ liệu đã nạp vào PostgreSQL và
trạng thái lịch sử trong checkpoint.

Kết quả:

* Sources trong PostgreSQL: 1
* Videos trong PostgreSQL: 8.021
* Transcript thành công trong Bronze JSONL: 290
* Tổng số dòng checkpoint: 304
* Số video duy nhất trong checkpoint: 302

---

### 2. Xây dựng loader transcript cho PostgreSQL

File:

```text
scripts/transcript_loading/load_transcripts_to_postgresql.py
```

Mục đích:

Kiểm tra và nạp dữ liệu từ Bronze transcript JSONL vào bảng `transcripts` mà
không tạo bản ghi trùng khi chạy lại.

Đã triển khai:

* Kiểm tra JSON không hợp lệ.
* Kiểm tra thiếu và trùng `video_id`.
* Kiểm tra toàn bộ `video_id` tồn tại trong bảng `videos`.
* Ghép `segments[].text` thành `raw_text`.
* Map `language_code` sang cột `language` hiện tại.
* Map `fetched_at` sang `retrieved_at`.
* Hỗ trợ dry-run và rollback trước khi commit.
* Bỏ qua video đã có transcript khi chạy lại.

Kết quả:

```text
Input Records    : 290
Existing Before : 0
Inserted        : 290
Database After  : 290
```

Chạy lại loader xác nhận:

```text
Already Existing : 290
Inserted         : 0
```

---

### 3. Xuất báo cáo JOIN video và transcript

File:

```text
scripts/data_audit/export_video_transcript_summary.py
reports/01_data_audit/video_transcript_summary.csv
```

Mục đích:

Xác minh transcript đã nạp có thể JOIN đầy đủ với metadata video.

Kết quả:

* Transcript trong PostgreSQL: 290
* Dòng JOIN được xuất: 290
* Transcript rỗng: 0
* Ngôn ngữ đã lưu: `en` = 290

---

### 4. Audit metadata, transcript và checkpoint

File:

```text
scripts/data_audit/audit_corpus.py
reports/01_data_audit/video_summary.csv
reports/01_data_audit/transcript_summary.csv
reports/01_data_audit/checkpoint_status_summary.csv
docs/reports/01_data_audit/CORPUS_AUDIT_REPORT.md
```

Mục đích:

Đánh giá chất lượng kỹ thuật và mức độ bao phủ của 290 transcript trước khi tiếp
tục phát triển downstream pipeline.

Kết quả:

* 290 transcript JOIN đầy đủ với video.
* Transcript rỗng: 0
* Video transcript thiếu description: 1
* Độ dài transcript: 439 đến 101.387 ký tự
* Độ dài trung vị: 27.212,5 ký tự
* Transcript chỉ phủ khoảng 3,62% toàn bộ catalog.
* 61 transcript có độ dài dưới 5.000 ký tự và cần kiểm tra nội dung.

Checkpoint là append-only. Trạng thái mới nhất theo 302 video:

```text
success              : 290
no_transcript        : 5
transcripts_disabled : 5
fetch_failed         : 1
ip_blocked           : 1
```

---

### 5. Báo cáo quá trình nạp transcript

File:

```text
docs/reports/01_data_audit/TRANSCRIPT_LOAD_REPORT.md
```

Mục đích:

Ghi lại nguồn dữ liệu, bước kiểm tra, field mapping, kết quả load và những trường
chưa được schema hiện tại biểu diễn.

Kết quả:

Không thay đổi schema. Các trường `is_generated`, segment count, segment timing,
tên ngôn ngữ đầy đủ và content hash vẫn được giữ trong Bronze JSONL.

---

### 6. Phân tách phạm vi commit của Ngày 7

Code:

```text
scripts/transcript_loading/load_transcripts_to_postgresql.py
scripts/data_audit/export_video_transcript_summary.py
scripts/data_audit/audit_corpus.py
```

Tài liệu:

```text
docs/status/CURRENT_STATUS.md
docs/reports/01_data_audit/TRANSCRIPT_LOAD_REPORT.md
docs/reports/01_data_audit/CORPUS_AUDIT_REPORT.md
docs/progress_log.md
```

Báo cáo dữ liệu:

```text
reports/01_data_audit/video_summary.csv
reports/01_data_audit/transcript_summary.csv
reports/01_data_audit/checkpoint_status_summary.csv
reports/01_data_audit/video_transcript_summary.csv
```

Các script và báo cáo CSV đã được commit riêng. Các file CSV có kích thước nhỏ,
không chứa `raw_text` đầy đủ và là snapshot có thể dùng để kiểm tra lại kết luận
trong tài liệu.

Không đưa vào commit này nếu chưa review riêng:

```text
README.md
docs/project_plan.md
docs/docs/transcripts_plan.md
src/database/load_transcripts.py
notebooks/
src/test/
src/quality/check.py
src/__init__.py
```

Các file trên là thay đổi có sẵn hoặc thuộc phạm vi khác, không nên trộn vào commit
audit và PostgreSQL loading.

---

### 7. Git History

Đã commit:

* `feat: add transcript loading and corpus audit scripts`
* `data: add transcript and corpus audit reports`

Commit tài liệu chưa được tạo. Các file tài liệu sẽ được stage và commit riêng sau
khi hoàn tất cập nhật `progress_log.md`.

---

# Những điều đã học được

## Số dòng checkpoint không phải số video

Đã hiểu:

* Checkpoint append-only có thể chứa nhiều dòng cho cùng một `video_id`.
* Tổng số dòng lịch sử là 304 nhưng chỉ đại diện cho 302 video.
* Báo cáo trạng thái hiện tại phải dùng trạng thái cuối cùng của từng video.

---

## Có transcript không đồng nghĩa corpus có phạm vi rõ ràng

Đã hiểu:

* 290 transcript hợp lệ về kỹ thuật nhưng chỉ phủ 3,62% channel.
* Chưa có playlist mapping nên chưa biết chúng thuộc course nào.
* Không nên bắt đầu chunking trước khi xác định corpus mục tiêu.

---

## Loader cần có dry-run và kiểm tra sau commit

Đã hiểu:

* Dry-run giúp kiểm tra transaction trước khi ghi dữ liệu.
* Foreign key cần được xác minh trước khi insert.
* Chạy lại loader phải không tạo dữ liệu trùng.
* Số dòng sau commit phải được kiểm tra bằng JOIN thực tế.

---

# Vấn đề còn tồn tại

Hiện tại:

* Chưa có quan hệ giữa video và playlist.
* Chưa phân loại 290 transcript theo course và domain.
* Có 61 transcript dưới 5.000 ký tự chưa được đánh giá.
* Có 1 video transcript thiếu description.
* Database chưa có unique constraint cho `transcripts.video_id`.
* Schema chưa lưu `is_generated`, segment metadata và content hash.

Không sửa schema ngay. Các giới hạn này phải được xem xét sau khi xác định phạm vi
corpus.

---

# Mục tiêu Ngày 8

## Mục tiêu chính

Phân tích title và description của 290 video để xác định course, domain và các
video rời rạc trước khi crawl playlist metadata.

---

## Bước 1

Phân tích pattern trong title và description.

---

## Bước 2

Gom nhóm video theo course hoặc chuỗi bài giảng có thể nhận diện từ metadata.

---

## Bước 3

Gom nhóm theo domain kiến thức ở mức tổng quát.

---

## Bước 4

Kiểm tra 61 transcript dưới 5.000 ký tự.

---

## Bước 5

Xuất:

```text
reports/02_corpus_analysis/transcript_distribution.csv
reports/02_corpus_analysis/course_distribution.csv
```

---

# Tiêu chí hoàn thành Ngày 8

Thành công nếu đạt được:

* Mỗi transcript có trạng thái phân loại rõ ràng hoặc được đánh dấu chưa xác định.
* Có thống kê transcript theo course và domain.
* Xác định được tỷ lệ video rời rạc.
* Có kết luận riêng cho nhóm transcript dưới 5.000 ký tự.
* Có cơ sở để thiết kế playlist mapping ở bước tiếp theo.

---

# Trạng thái tổng thể dự án

Phase 1 - Foundation

✅ Hoàn thành

---

Phase 2 - Metadata và Transcript Ingestion

✅ Hoàn thành cho corpus hiện tại

---

Phase 3 - Data Foundation Audit

✅ Hoàn thành

---

Phase 4 - Corpus Analysis và Playlist Mapping

🟨 Đang thực hiện

---

Phase 5 - Transcript Cleaning và Chunking

⬜ Tạm dừng đến khi xác định corpus

---

Phase 6 - Embedding và Semantic Search

⬜ Chưa bắt đầu

---

# Ngày 8 - Corpus Course và Domain Analysis

## Đã hoàn thành

### 1. Xây dựng script phân tích corpus

File:

```text
scripts/corpus_analysis/analyze_corpus.py
```

Mục đích:

Phân tích 290 transcript theo course, domain và độ dài bằng metadata hiện có mà
không ghi ngược kết quả vào PostgreSQL.

Đã triển khai:

* Nhận diện mã course từ title và description.
* Yêu cầu bằng chứng `MIT` rõ ràng trước khi nhận một chuỗi là course code.
* Gắn trạng thái `unresolved` khi metadata không đủ.
* Phân loại domain bằng mã khoa và từ khóa.
* Đánh dấu mức độ ưu tiên kiểm tra cho transcript dưới 5.000 ký tự.
* Xuất bằng chứng và rule phân loại theo từng transcript.

---

### 2. Phân tích phân bố course

File:

```text
reports/02_corpus_analysis/transcript_classification.csv
reports/02_corpus_analysis/course_distribution.csv
```

Kết quả:

* Tổng transcript: 290
* Nhận diện được course code: 258
* Chưa nhận diện được course code: 32
* Số course code đã nhận diện: 134
* Course chỉ có 1 transcript: 72
* Course có ít nhất 4 transcript: 16
* Course lớn nhất: `RES.6-012`, có 11 transcript

Kết luận:

Corpus phân tán trên nhiều course. Không có course nào chiếm tỷ trọng đủ lớn để
coi 290 transcript là một corpus course tập trung.

---

### 3. Phân tích phân bố domain

File:

```text
reports/02_corpus_analysis/transcript_distribution.csv
```

Kết quả:

```text
computer_science_ai_data           : 46
mathematics_statistics             : 45
physics                            : 44
unresolved                         : 42
engineering                        : 38
economics_business_management      : 33
biology_medicine_neuroscience      : 24
education_communication_media      : 8
humanities_social_science          : 8
architecture_urban_studies         : 2
```

Domain là phân loại heuristic nội bộ, không phải taxonomy chính thức của MIT.

---

### 4. Kiểm tra transcript ngắn

File:

```text
reports/02_corpus_analysis/short_transcript_review.csv
```

Kết quả:

* Transcript dưới 5.000 ký tự: 61
* Duration: 41–547 giây
* Duration trung bình: 241,69 giây
* `likely_valid_short_video`: 61
* `possible_incomplete`: 0

Chưa có bằng chứng kỹ thuật cho thấy 61 transcript này bị cắt. Không loại bỏ chúng.

---

### 5. Hoàn thành báo cáo phân tích corpus

File:

```text
docs/reports/02_corpus_analysis/CORPUS_ANALYSIS_REPORT.md
docs/status/CURRENT_STATUS.md
```

Kết quả:

Ghi lại phương pháp, kết quả, false positive đã loại, giới hạn của heuristic và
quyết định chuyển sang playlist mapping.

---

# Những điều đã học được

## Regex có thể tạo false positive

Đã hiểu:

* Chuỗi giống course code không đồng nghĩa là course code.
* `fall-2004`, `DD.2.1`, `COVID-19` và `HS-002` từng bị nhận nhầm.
* Domain `mit.edu` trong URL không được dùng như bằng chứng tiền tố `MIT`.
* Khi không đủ bằng chứng cần giữ `unresolved` thay vì ép nhãn.

---

## Corpus size không phản ánh corpus coherence

Đã hiểu:

* 290 transcript đủ để chạy thử pipeline kỹ thuật.
* 290 transcript không tạo thành corpus tập trung khi trải trên 134 course.
* 72 course chỉ có một transcript cho thấy sampling bị phân tán.
* Cần đo coverage theo playlist/course trước khi semantic evaluation.

---

## Transcript ngắn không đồng nghĩa transcript lỗi

Đã hiểu:

* Độ dài transcript phải được xem cùng duration video.
* 61 transcript ngắn đều thuộc video dưới 10 phút.
* Không được xóa dữ liệu chỉ dựa trên ngưỡng ký tự.

---

# Vấn đề còn tồn tại

Hiện tại:

* 32 transcript chưa nhận diện được course.
* 42 transcript chưa nhận diện được domain.
* Chưa biết tổng số video của từng course.
* Chưa có quan hệ video–playlist.
* Một video có thể nằm trong nhiều playlist nhưng báo cáo hiện chưa biểu diễn được.
* Joint course có thể chỉ giữ mã course đầu tiên.

---

# Mục tiêu Ngày 9

## Mục tiêu chính

Khôi phục quan hệ giữa 290 video transcript và playlist mà không tải lại transcript
hoặc metadata video.

---

## Bước 1

Thu thập danh sách playlist của MIT OpenCourseWare.

---

## Bước 2

Thu thập playlist items và chỉ giữ các trường cần thiết cho mapping.

---

## Bước 3

Tạo:

```text
playlists.csv
video_playlist.csv
```

---

## Bước 4

JOIN mapping với 290 video transcript.

---

## Bước 5

Đo coverage theo playlist và kiểm tra 32 course unresolved, 42 domain unresolved.

---

# Tiêu chí hoàn thành Ngày 9

Thành công nếu đạt được:

* Có danh sách playlist và playlist items hợp lệ.
* Biểu diễn được quan hệ nhiều–nhiều giữa video và playlist.
* Biết bao nhiêu trong 290 video nằm trong ít nhất một playlist.
* Không tải lại transcript.
* Không crawl lại toàn bộ channel metadata.
* Có báo cáo coverage để quyết định corpus mục tiêu.

---

# Trạng thái tổng thể dự án

Phase 1 - Foundation

✅ Hoàn thành

---

Phase 2 - Metadata và Transcript Ingestion

✅ Hoàn thành cho corpus hiện tại

---

Phase 3 - Data Foundation Audit

✅ Hoàn thành

---

Phase 4 - Corpus Analysis

✅ Hoàn thành bước phân tích metadata

---

Phase 5 - Playlist Mapping

🟨 Bước tiếp theo

---

Phase 6 - Transcript Cleaning và Chunking

⬜ Tạm dừng đến khi xác định corpus

---

Phase 7 - Embedding và Semantic Search

⬜ Chưa bắt đầu

---

# Ngày 9 - Playlist Mapping

## Đã hoàn thành

### 1. Tổ chức lại report theo milestone

File:

```text
reports/README.md
reports/01_data_audit/
reports/02_corpus_analysis/
reports/03_playlist_mapping/
```

Mục đích:

Tách báo cáo theo từng bước để dễ theo dõi nguồn gốc, script tạo dữ liệu và quyết
định tương ứng.

---

### 2. Xây dựng playlist mapping pipeline

File:

```text
scripts/playlist_mapping/map_playlists.py
```

Đã triển khai:

* Thu public playlists bằng pagination.
* Thu playlist items bằng pagination.
* Chỉ giữ mapping liên quan đến 290 video transcript.
* Loại uploads playlist khỏi phân tích course.
* Checkpoint sau từng playlist để hỗ trợ resume.
* Deduplicate theo cặp `video_id + playlist_id`.
* Không tải lại transcript hoặc video metadata.

---

### 3. Hoàn thành mapping và kiểm tra coverage

File:

```text
reports/03_playlist_mapping/playlists.csv
reports/03_playlist_mapping/video_playlist.csv
reports/03_playlist_mapping/playlist_coverage.csv
reports/03_playlist_mapping/playlist_distribution.csv
```

Kết quả:

```text
Public curated playlists : 361
Video-playlist rows       : 284
Mapped transcript videos  : 283
Unmapped videos           : 7
Videos in >1 playlist     : 1
Duplicate mapping pairs   : 0
```

---

### 4. Bổ sung course và domain từ playlist title

Kết quả:

* Course unresolved trước playlist: 32
* Course unresolved sau playlist fallback: 25
* Domain unresolved trước playlist: 42
* Domain unresolved sau playlist fallback: 38

Playlist chỉ được dùng làm fallback khi metadata đang unresolved và các playlist
có nhãn thống nhất. Không ghi đè course/domain đã có.

---

### 5. Hoàn thành báo cáo playlist mapping

File:

```text
docs/reports/03_playlist_mapping/PLAYLIST_MAPPING_REPORT.md
docs/status/CURRENT_STATUS.md
```

Kết luận:

Corpus hiện tại có coverage playlist cao về membership nhưng coverage thấp trong
từng course. Không cần crawl lại toàn bộ channel; cần chọn corpus mục tiêu trước.

---

# Những điều đã học được

## Playlist mapping là quan hệ nhiều–nhiều

Đã hiểu:

* Một video có thể nằm trong nhiều playlist.
* Mapping cần bảng nối hoặc file quan hệ riêng.
* Không nên lưu một `playlist_id` duy nhất trực tiếp trong video.

---

## Có playlist không đồng nghĩa xác định được course

Đã hiểu:

* 31/32 video course-unresolved có playlist membership.
* Chỉ 7 video có playlist title đủ rõ để bổ sung course code.
* Playlist title không chuẩn phải giữ unresolved thay vì ép nhãn.

---

## Playlist coverage xác nhận corpus sampling bị phân tán

Đã hiểu:

* Playlist lớn nhất có 266 items nhưng corpus chỉ có 11 transcript match.
* 283 video có playlist không có nghĩa các course đã đủ coverage.
* Corpus selection phải xảy ra trước targeted crawl.

---

# Vấn đề còn tồn tại

* 7 video không có public playlist mapping.
* 25 video vẫn chưa xác định course.
* 38 video vẫn chưa xác định domain.
* Chưa chọn course hoặc domain mục tiêu.
* Chưa đặt ngưỡng coverage tối thiểu cho corpus.
* Chưa quyết định crawl bổ sung playlist nào.

---

# Mục tiêu Ngày 10

## Mục tiêu chính

Ra quyết định phạm vi corpus dựa trên playlist mapping, course distribution và mục
tiêu semantic search.

---

## Bước 1

Chọn một hoặc một nhóm course/domain mục tiêu.

---

## Bước 2

Tính coverage transcript trên tổng số item của playlist được chọn.

---

## Bước 3

Lập danh sách video còn thiếu transcript trong playlist mục tiêu.

---

## Bước 4

Quyết định giữ corpus hiện tại hay targeted crawl.

---

## Bước 5

Tạo:

```text
docs/CORPUS_SCOPE.md
reports/04_scope_decision/
```

---

# Tiêu chí hoàn thành Ngày 10

* Có corpus mục tiêu được mô tả rõ.
* Có playlist/course nằm trong scope.
* Có coverage hiện tại và coverage mục tiêu.
* Có danh sách video cần crawl bổ sung nếu thiếu.
* Không quay lại crawl toàn bộ channel.

---

# Trạng thái tổng thể dự án

Phase 1 - Foundation

✅ Hoàn thành

---

Phase 2 - Metadata và Transcript Ingestion

✅ Hoàn thành cho corpus hiện tại

---

Phase 3 - Data Foundation Audit

✅ Hoàn thành

---

Phase 4 - Corpus Analysis

✅ Hoàn thành

---

Phase 5 - Playlist Mapping

✅ Hoàn thành

---

Phase 6 - Scope Decision

🟨 Bước tiếp theo

---

Phase 7 - Transcript Cleaning và Chunking

⬜ Tạm dừng đến khi xác định corpus

---

Phase 8 - Embedding và Semantic Search

⬜ Chưa bắt đầu

---

# Ngày 10 - Corpus Scope Decision và Project Reorganization

## Đã hoàn thành

### 1. Chọn corpus mục tiêu

Quyết định:

```text
MIT 6.0001 Introduction to Computer Science and Programming in Python
Fall 2016
Playlist ID: PLUl4u3cNGP63WbdFxL8giv4yhgdMGaZNA
Playlist items: 38
Current transcripts: 4
Initial gap: 34
```

Lý do:

* Phạm vi course rõ ràng.
* Người phát triển có kiến thức Python để manual review.
* Quy mô phù hợp cho MVP và evaluation.
* Không cần crawl lại toàn bộ channel.

File quyết định:

```text
docs/decisions/CORPUS_SCOPE.md
```

---

### 2. Lập kế hoạch triển khai MIT 6.0001

File:

```text
docs/plans/MIT_60001_IMPLEMENTATION_PLAN.md
```

Kế hoạch gồm:

* Target inventory và gap report.
* Targeted transcript acquisition.
* PostgreSQL reconciliation.
* Transcript cleaning.
* Chunking experiment.
* Embedding và vector index.
* Retrieval API có citation.
* Evaluation chống hallucination.

---

### 3. Tổ chức lại scripts

```text
scripts/
├── transcript_loading/
├── data_audit/
├── corpus_analysis/
├── playlist_mapping/
└── target_corpus/
```

Mỗi folder là Python package và chỉ chứa script thuộc đúng chức năng.

---

### 4. Tổ chức lại docs

```text
docs/
├── README.md
├── status/
├── decisions/
├── plans/
└── reports/
    ├── 01_data_audit/
    ├── 02_corpus_analysis/
    └── 03_playlist_mapping/
```

Các tài liệu lịch sử như architecture, project plan và progress log vẫn ở vị trí
cũ để tránh trộn thay đổi chưa review.

---

### 5. Chuẩn bị report folders cho bước tiếp theo

```text
reports/04_scope_decision/
reports/05_target_corpus/
```

Folder có README mô tả output dự kiến. Chưa tạo CSV giả trước khi inventory chạy.

---

# Những điều đã học được

## Scope phải được điều khiển bằng manifest

Đã hiểu:

* Không cần xóa 286 transcript ngoài scope.
* Target manifest quyết định dữ liệu nào được clean, chunk và embedding.
* Giữ raw source chung tránh tạo nhiều bản sao transcript.

---

## Evaluation cần dựa trên nguồn và khả năng từ chối

Đã hiểu:

* Kiến thức Python giúp manual review nhưng không thay thế test set.
* Câu trả lời cần citation video và timestamp.
* Câu hỏi ngoài scope phải được dùng để đo abstention.
* Không tuyên bố hệ thống là trợ lý Python tổng quát.

---

# Vấn đề còn tồn tại

* Chưa có inventory chi tiết của đủ 38 playlist items.
* Chưa xác định video nào trong 34 gap thực sự có transcript.
* Chưa targeted crawl.
* Chưa quyết định cách giữ segment timing sau PostgreSQL migration.
* Chưa có evaluation dataset.

---

# Mục tiêu Ngày 11

## Mục tiêu chính

Tạo target inventory, gap report và manifest cho đúng 38 video MIT 6.0001 trước
khi gọi transcript API.

---

# Tiêu chí hoàn thành Ngày 11

* Có đúng 38 video ID duy nhất theo playlist position.
* Xác nhận 4 transcript hiện có.
* Có danh sách video cần fetch và video đã có trạng thái cuối.
* Không đưa video ngoài playlist vào target manifest.
* Chưa fetch transcript trước khi gap report được kiểm tra.

---

# Trạng thái tổng thể dự án

Phase 1 - Data Foundation và Audit

✅ Hoàn thành

---

Phase 2 - Corpus Analysis và Playlist Mapping

✅ Hoàn thành

---

Phase 3 - Scope Decision

✅ MIT 6.0001 Fall 2016

---

Phase 4 - Target Inventory và Acquisition

🟨 Bước tiếp theo

---

Phase 5 - Cleaning, Chunking và Indexing

⬜ Chưa bắt đầu

---

Phase 6 - Retrieval và Evaluation

⬜ Chưa bắt đầu

---

# Ngày 11 - MIT 6.0001 Target Inventory

## Đã hoàn thành

### 1. Xây dựng target inventory script

File:

```text
scripts/target_corpus/build_target_inventory.py
```

Đã triển khai:

* Lấy playlist items bằng YouTube Data API.
* Validate đúng 38 items và 38 video ID duy nhất.
* Validate position liên tục từ 0 đến 37.
* Đối chiếu metadata PostgreSQL.
* Đối chiếu transcript Bronze JSONL và PostgreSQL.
* Đọc trạng thái checkpoint mới nhất theo video.
* Phân loại fetch candidate và trường hợp cần manual review.
* Bảo vệ manifest v1 khỏi ghi đè khi playlist thay đổi.

Script không gọi transcript API.

---

### 2. Tạo inventory, gap report và manifest

File:

```text
reports/04_scope_decision/target_playlist_inventory.csv
reports/04_scope_decision/target_gap_report.csv
reports/04_scope_decision/target_manifest.csv
```

Kết quả:

```text
Playlist items      : 38
Unique video IDs    : 38
Positions           : 0..37
Already available   : 4
Not attempted       : 34
Fetch candidates    : 34
Manual review       : 0
```

---

### 3. Version target manifest

```text
scope_version: mit_60001_fall_2016_v1
SHA-256: f8f9108a3dc910219e2e915e83519c7054afc9c2783714b94ecdc145c150fda4
```

Khi playlist khác manifest hiện có, script dừng và yêu cầu scope version mới thay
vì ghi đè v1.

---

### 4. Hoàn thành báo cáo inventory

File:

```text
docs/reports/04_scope_decision/TARGET_INVENTORY_REPORT.md
docs/status/CURRENT_STATUS.md
```

Kết luận:

34 video gap đều là `not_attempted`. Không có video target nào đã mang trạng thái
`no_transcript`, `transcripts_disabled` hoặc lỗi retryable trong checkpoint.

---

# Những điều đã học được

## Gap không đồng nghĩa failure

Đã hiểu:

* 34 video thiếu chưa từng được transcript pipeline xử lý.
* Không được báo cáo chúng là transcript fail.
* Transcript availability chỉ biết sau targeted acquisition.

---

## Manifest cần bất biến

Đã hiểu:

* Playlist công khai có thể thay đổi theo thời gian.
* Manifest version bảo vệ tính tái lập của corpus và evaluation.
* Thay đổi scope phải tạo manifest version mới.

---

# Vấn đề còn tồn tại

* Chưa biết bao nhiêu trong 34 video cung cấp transcript tiếng Anh.
* Chưa xây dựng target-only transcript queue.
* Chưa chạy targeted acquisition.
* Chưa reconcile kết quả acquisition vào PostgreSQL.

---

# Mục tiêu Ngày 12

## Mục tiêu chính

Xây dựng targeted transcript acquisition chỉ đọc 34 fetch candidates trong
manifest MIT 6.0001 v1.

---

# Tiêu chí hoàn thành Ngày 12

* Pipeline từ chối video ngoài manifest.
* Hỗ trợ checkpoint, resume, delay và stop-on-block.
* Không fetch lại 4 transcript đã có.
* Mỗi video có trạng thái rõ ràng sau lần chạy.
* Có acquisition status và coverage report.

---

# Trạng thái tổng thể dự án

Phase 1 - Data Foundation, Corpus Analysis và Scope

✅ Hoàn thành

---

Phase 2 - Target Inventory

✅ Hoàn thành

---

Phase 3 - Targeted Transcript Acquisition

🟨 Bước tiếp theo

---

Phase 4 - Cleaning, Chunking và Indexing

⬜ Chưa bắt đầu

---

Phase 5 - Retrieval và Evaluation

⬜ Chưa bắt đầu

---

# Ngày 12 - Targeted Transcript Crawler Build

## Đã hoàn thành

### 1. Xây dựng target-only transcript crawler

File:

```text
scripts/target_corpus/fetch_target_transcripts.py
```

Đã triển khai:

* Validate manifest v1 gồm 38 video.
* Chỉ đọc 34 reviewed fetch candidates từ gap report.
* Từ chối video ngoài manifest.
* Từ chối video không phải fetch candidate.
* Mặc định planning mode, cần `--execute` để gọi API.
* Bỏ qua payload đã tồn tại.
* Hỗ trợ limit, delay, runtime limit và failure threshold.
* Dừng khi gặp IP block, request block hoặc rate limit.
* Ghi checkpoint kèm scope version và pipeline name.
* Tạo acquisition status và summary report.

---

### 2. Kiểm tra planning queue

Kết quả:

```text
Manifest videos     : 38
Reviewed candidates : 34
Queued videos       : 34
Payload available   : 4
Not attempted       : 34
Transcript requests : 0
```

---

### 3. Kiểm tra scope guard

* ID ngoài manifest bị từ chối.
* Video đã có transcript bị từ chối vì không phải fetch candidate.
* Cả hai guard đều dừng trước transcript request.

---

### 4. Tạo baseline report

File:

```text
reports/05_target_corpus/acquisition_status.csv
reports/05_target_corpus/acquisition_summary.csv
docs/reports/05_target_corpus/TARGET_ACQUISITION_BASELINE.md
```

---

# Vấn đề còn tồn tại

* Chưa chạy transcript API trên target queue.
* Chưa biết transcript availability thực tế của 34 video.
* Chưa kiểm tra payload mới và checkpoint sau request thật.

---

# Mục tiêu Ngày 13

Chạy thử tối đa 3 target videos với delay 20–60 giây, sau đó kiểm tra Bronze,
checkpoint và acquisition report trước khi quyết định chạy phần còn lại.

---

# Tiêu chí hoàn thành Ngày 13

* Không fetch video ngoài manifest.
* Không fetch lại 4 payload hiện có.
* Mỗi request tạo payload hoặc checkpoint status rõ ràng.
* Pipeline dừng an toàn nếu bị block.
* Chưa chạy toàn bộ queue nếu test nhỏ chưa được review.

---

# Ngày 13 - MIT 6.0001 Targeted Transcript Acquisition

## Đã hoàn thành

### 1. Chạy target-only transcript crawler

Đã chạy crawler với `--execute` trên queue thuộc manifest:

```text
scope_version: mit_60001_fall_2016_v1
Target videos: 38
Payload có sẵn trước acquisition: 4
Payload mới thu thập: 34
```

Crawler không mở rộng ra ngoài manifest và không fetch lại bốn payload đã tồn tại.

---

### 2. Kiểm tra kết quả acquisition

Nguồn kiểm tra:

```text
data/bronze/transcripts_raw.jsonl
data/bronze/transcripts_checkpoint.jsonl
reports/05_target_corpus/acquisition_status.csv
reports/05_target_corpus/acquisition_summary.csv
```

Kết quả:

```text
Bronze payload total       : 324
Bronze unique video IDs    : 324
Target payloads            : 38/38
Target success checkpoints : 38/38
Not attempted              : 0
Permanently unavailable    : 0
Retryable failures         : 0
Manual review              : 0
```

Target corpus MIT 6.0001 đã đạt transcript coverage 100% theo manifest v1.

---

### 3. Validate PostgreSQL loader bằng dry-run

Đã chạy:

```powershell
python -X utf8 scripts/transcript_loading/load_transcripts_to_postgresql.py
```

Kết quả:

```text
Mode             : DRY RUN
Input records    : 324
Already existing : 290
Inserted         : 34
Before count     : 290
After count      : 324
```

Transaction đã rollback. PostgreSQL vẫn có 290 transcript; chưa có thay đổi dữ liệu
được lưu.

---

### 4. Phạm vi commit đề xuất

Nên tạo checkpoint Git tại đây trước khi load PostgreSQL. Tách theo loại thay đổi:

```text
feat: add MIT 6.0001 target transcript acquisition pipeline
data: add MIT 6.0001 target corpus acquisition reports
docs: document completed MIT 6.0001 transcript acquisition
```

Không commit `data/bronze/` vì đây là dữ liệu raw cục bộ và đã nằm trong
`.gitignore`. Không đưa `notebooks/`, `src/test/`, `src/quality/check.py` hoặc các
thay đổi ngoài target corpus vào cùng commit nếu chưa review riêng.

---

# Những điều đã học được

## Acquisition hoàn thành chưa đồng nghĩa PostgreSQL đã được cập nhật

Đã hiểu:

* Bronze là source of truth của payload vừa crawl.
* PostgreSQL vẫn giữ 290 transcript cho đến khi chạy loader với `--commit`.
* Dry-run chỉ validate và mô phỏng transaction, sau đó rollback.
* Phải kiểm tra count và JOIN sau khi commit trước khi chuyển sang Silver.

---

# Vấn đề còn tồn tại

* 34 transcript mới chưa được lưu vào PostgreSQL.
* Chưa chạy truy vấn xác nhận 38/38 target video có transcript sau database load.
* Chưa thiết kế schema và quy tắc làm sạch Silver transcript.

---

# Mục tiêu Ngày 14

## Mục tiêu chính

Load 34 transcript mới vào PostgreSQL, xác minh target coverage 38/38 bằng JOIN,
sau đó đóng mốc Transcript Ingestion.

---

# Tiêu chí hoàn thành Ngày 14

* Loader commit chèn đúng 34 dòng và tổng bảng `transcripts` đạt 324.
* Chạy lại loader ở dry-run cho kết quả `Inserted: 0`.
* JOIN manifest, `videos` và `transcripts` trả về đủ 38 target videos.
* Không có `raw_text` rỗng và mọi target transcript có language hợp lệ.
* Có báo cáo PostgreSQL load và truy vấn kiểm chứng.

---

# Trạng thái tổng thể dự án

Phase 1 - Data Foundation, Corpus Analysis và Scope

✅ Hoàn thành

---

Phase 2 - Target Inventory

✅ Hoàn thành

---

Phase 3 - Targeted Transcript Acquisition

✅ Hoàn thành

---

Phase 4 - PostgreSQL Load và Validation

🟨 Bước tiếp theo

---

Phase 5 - Cleaning, Chunking và Indexing

⬜ Chưa bắt đầu

---

Phase 6 - Retrieval và Evaluation

⬜ Chưa bắt đầu

---

# Ngày 14 - PostgreSQL Load và Target Validation

## Đã hoàn thành

### 1. Load transcript vào PostgreSQL

Đã chạy loader với `--commit`:

```powershell
python -X utf8 scripts/transcript_loading/load_transcripts_to_postgresql.py --commit
```

Kết quả:

```text
Input records    : 324
Already existing : 290
Inserted         : 34
Before count     : 290
After count      : 324
```

34 transcript mới đã được lưu. Tổng bảng `transcripts` tăng từ 290 lên 324.

---

### 2. Kiểm tra idempotency

Loader được chạy lại không có `--commit`. Không có bản ghi mới cần chèn và
transaction được rollback.

Kết luận: chạy lại loader không tạo transcript trùng theo `video_id`.

---

### 3. Kiểm tra JOIN target corpus

Đã JOIN target manifest với `videos` và `transcripts` bằng kết nối read-only:

```text
Total PostgreSQL transcripts : 324
Target JOIN rows             : 38
Target unique videos         : 38
Missing video metadata       : 0
Missing target transcripts   : 0
Duplicate target transcripts : 0
Empty raw_text               : 0
Empty language               : 0
```

Transcript length:

```text
Minimum : 653
Maximum : 49.645
Average : 13.243
```

Độ dài ngắn nhất không được xem tự động là lỗi vì transcript vẫn có nội dung.

---

### 4. Tạo validator và báo cáo

File:

```text
scripts/transcript_loading/validate_target_postgresql.py
reports/06_transcript_load_validation/validation_summary.csv
reports/06_transcript_load_validation/target_transcript_validation.csv
docs/reports/06_transcript_load_validation/POSTGRESQL_TARGET_LOAD_REPORT.md
```

Validator đọc video ID từ manifest, dùng transaction PostgreSQL read-only và
không xuất `raw_text` vào CSV.

Kết quả:

```text
validation_status: passed
```

---

# Những điều đã học được

## Validation cần kiểm tra coverage, không chỉ kiểm tra tổng count

Đã hiểu:

* Tổng 324 dòng không tự chứng minh target corpus đủ 38 video.
* Cần JOIN theo manifest để phát hiện video target bị thiếu.
* Cần kiểm tra duplicate, `raw_text`, `language` và tính idempotent.
* CSV validation không cần chứa nội dung transcript đầy đủ.

---

# Vấn đề còn tồn tại

* Schema hiện tại chưa lưu segment timing, `is_generated` và content hash.
* Chưa định nghĩa Silver transcript schema.
* Chưa xác định cleaning rules cho code, toán tử và whitespace.
* Chưa tạo semantic chunks.

---

# Mục tiêu Ngày 15

## Mục tiêu chính

Thiết kế Silver transcript contract cho MIT 6.0001 trước khi viết cleaning
pipeline.

---

# Tiêu chí hoàn thành Ngày 15

* Xác định field bắt buộc của Silver transcript.
* Quyết định cách giữ segment timing và `is_generated`.
* Định nghĩa cleaning version và content hash.
* Phân biệt normalization an toàn với sửa nội dung bằng phỏng đoán.
* Có sample validation trên một nhóm transcript trước khi xử lý đủ 38 video.

---

# Trạng thái tổng thể dự án

Phase 1 - Data Foundation, Corpus Analysis và Scope

✅ Hoàn thành

---

Phase 2 - Target Inventory

✅ Hoàn thành

---

Phase 3 - Targeted Transcript Acquisition

✅ Hoàn thành

---

Phase 4 - PostgreSQL Load và Validation

✅ Hoàn thành

---

Phase 5 - Silver Transcript Design và Cleaning

🟨 Bước tiếp theo

---

Phase 6 - Chunking, Retrieval và Evaluation

⬜ Chưa bắt đầu

---

# Ngày 15 - Silver Transcript Cleaning

## Đã hoàn thành

### 1. Audit Bronze và quyết định storage

Đã audit 38 target Bronze payload trước khi cleaning. Kết quả có 12.518 segment,
không có segment rỗng hoặc timing sai thứ tự; 9.048 segment có internal newline và
1.450 adjacent pair có timing overlap.

Đã chọn Silver JSONL làm nguồn segment cho chunking/citation. PostgreSQL giữ
normalized transcript và video metadata, không migration schema trong bước này.

### 2. Silver contract và lossless cleaning policy

Đã chốt:

```text
schema_version: silver_transcript_v1
cleaning_version: mit_60001_clean_v1
scope_version: mit_60001_fall_2016_v1
```

V1 không sửa `segments[].text`, không strip/collapse whitespace, không decode HTML,
không xóa caption cue, không deduplicate và không sửa timing. Silver chỉ ánh xạ
field, thêm manifest metadata, lineage, hash và transcript text dẫn xuất.

### 3. Sample và full validation

Sample năm video pass JSON Schema, text/timing equality, source/content hash và
independent rebuild. Sau đó full builder dùng cùng core để xử lý đủ 38 video.

```text
Silver records: 38/38
Unique video IDs: 38
Positions: 0..37
Total segments: 12,518
Failed validations: 0
Full output SHA-256: 50d559529bedc33715b13312c5e4b7def80ac808521b53699a14465e084a8ecb
Cross-process deterministic: passed
```

### 4. Output và tài liệu

```text
data/silver/mit_60001/transcripts_clean.jsonl
reports/07_cleaning/full_validation.csv
reports/07_cleaning/cleaning_summary.csv
docs/reports/07_cleaning/DAILY_REPORT_2026-07-26.md
docs/reports/07_cleaning/SILVER_FULL_BUILD_REPORT.md
```

Silver JSONL là generated data đã gitignore; các report không chứa transcript text.

---

# Những điều đã học được

* Cleaning lossless và semantic chunking là hai bước khác nhau. Silver không được
  sửa text để phục vụ thuật toán chunking.
* Determinism cần được kiểm tra bằng hai lần build độc lập; serialize cùng một
  object trong bộ nhớ chỉ kiểm tra một phần nhỏ hơn.
* Report validation cần dùng kết quả có cấu trúc thay vì suy luận từ wording của
  error message.

---

# Vấn đề còn tồn tại

* Chưa có Gold chunk contract.
* Chưa chọn token guardrail, semantic boundary strategy hoặc fixed-token baseline.
* Chưa có evaluation set để chọn cấu hình chunking.
* Chưa tạo embedding, vector index, retrieval API hoặc evaluation pipeline.

---

# Mục tiêu milestone kế tiếp

Thiết kế chunking experiment trên Silver v1: Gold chunk schema, lineage, semantic
boundary, token guardrail, baseline và evaluation criteria trước khi generate chunk.

---

# Trạng thái tổng thể dự án

Phase 1 - Data Foundation, Corpus Analysis và Scope

✅ Hoàn thành

---

Phase 2 - Target Inventory

✅ Hoàn thành

---

Phase 3 - Targeted Transcript Acquisition

✅ Hoàn thành

---

Phase 4 - PostgreSQL Load và Validation

✅ Hoàn thành

---

Phase 5 - Silver Transcript Design và Cleaning

✅ Hoàn thành

---

Phase 6 - Chunking, Retrieval và Evaluation

⬜ Chưa bắt đầu

---

# Ngày 16 - Chunking Experiment Design và Sample Validation

## Đã hoàn thành

* Audit code chunking cũ: `src/processing/chunking.py` là file rỗng, không tái sử dụng.
* Chốt Gold contract/schema với lineage tới Silver range, lossless chunk text và citation timing.
* Chốt ba configuration: fixed-token baseline, semantic cosine 240 và semantic cosine 192 có overlap.
* Chọn MiniLM cho sample iteration, pin encoder revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.
* Tạo evaluation contract/template trống; chỉ human-approved question mới là ground truth.
* Build và validate năm video sample cho cả ba configuration.

```text
Fixed baseline chunks: 178
Semantic 240 chunks: 285
Semantic 192 + overlap chunks: 350
Source coverage: complete cho cả ba
Schema errors: 0
Cross-process deterministic: passed cho cả ba
```

## Vấn đề còn tồn tại

* Evaluation template chưa có question `approved`.
* Chưa có retrieval metrics để chọn configuration.
* Chưa build Gold đầy đủ 38 video.
* Chưa tạo embedding, vector index hoặc retrieval API.

## Mục tiêu milestone kế tiếp

Soạn/review evaluation questions có video ID và timestamp evidence, sau đó chạy
retrieval comparison trước khi duyệt full Gold build.

---

# Trạng thái tổng thể dự án

Phase 1 - Data Foundation, Corpus Analysis và Scope

✅ Hoàn thành

---

Phase 2 - Target Inventory

✅ Hoàn thành

---

Phase 3 - Targeted Transcript Acquisition

✅ Hoàn thành

---

Phase 4 - PostgreSQL Load và Validation

✅ Hoàn thành

---

Phase 5 - Silver Transcript Design và Cleaning

✅ Hoàn thành

---

Phase 6 - Chunking, Retrieval và Evaluation

🟨 Chunking sample đã pass; evaluation và full Gold chưa bắt đầu

---

# Ngày 17 - Batch 01 Evaluation Source Review và Canonicalization

## Đã hoàn thành

### 1. Human source review và decision ledger

Batch 01 được review theo source candidates có transcript excerpt. Kết quả final
canonical là 13 record `approved`: 11 answerable và hai câu out-of-scope. q-011
chưa được canonicalize do evidence so sánh recursion/iteration chưa được duyệt.

### 2. Rewrite và source candidate v2

q-003 được rewrite sang variable names across scopes; q-004 được rewrite để phân
biệt assignment `=` với equality `==`. Locator chạy lại và tạo candidate v2 gồm 62
dòng. File v2 là source candidate hiện hành; candidate cũ được giữ để audit.

q-005 dùng source expansion Silver segments 105–116 (`WPSeyjX1-4s`,
294.720–325.870), được human final approve. q-011 có source expansion nhưng chưa
được approve.

### 3. Canonical evaluation subset và validation

Đã tạo `evaluation/mit_60001/evaluation_questions.jsonl`:

```text
Canonical records : 13
Approved          : 13
Answerable        : 11
Out of scope      : 2
Duplicate IDs     : 0
```

Mỗi answerable record có expected answer points, video ID và exact time range.
Validation read-only pass parse JSONL, contract fields/conditions, time-range order,
v2 evidence ranges, q-005 source expansion và q-011 exclusion.

## Vấn đề còn tồn tại

* q-011 chưa có evidence so sánh recursion và iteration được duyệt.
* Batch 01 mới có 13 approved records, chưa đạt mục tiêu 40–60 câu.
* Chưa có retrieval comparison, lựa chọn Gold configuration hoặc Gold full corpus.
* Chưa xây embedding/index, Hybrid Search, Cross-Encoder, LLM runtime hoặc Search API.

## Mục tiêu milestone kế tiếp

Mở rộng evaluation set lên 40–60 approved questions, xử lý q-011, rồi chạy retrieval
comparison ba configuration bằng cùng approved question set trước khi duyệt Gold full.

## Trạng thái tổng thể dự án

Phase 1 - Data Foundation, Corpus Analysis và Scope

✅ Hoàn thành

---

Phase 2 - Target Inventory, Acquisition, PostgreSQL và Silver

✅ Hoàn thành

---

Phase 3 - Chunking Sample

✅ Sample ba configuration đã pass; Gold full chưa build

---

Phase 4 - Evaluation

🟨 Batch 01 có 13 approved records; cần đạt 40–60 câu trước retrieval comparison

---

Phase 5 - Retrieval và Runtime

⬜ Chưa bắt đầu

---

# Ngày 18 - Batch 02 Draft Coverage, Candidate Package và Decision Record

## Đã hoàn thành

### 1. Batch 02 coverage-balanced draft

Tạo 30 draft `mit60001-q-015` đến `mit60001-q-044` và tạo Coverage Matrix.
Sau human feedback, sáu wording được thay để bổ sung Strings, Dictionaries, List
indexing, Searching và Sorting; q-028 assertion failure và q-032 unhandled
exception được giữ nguyên. Batch 02 vẫn đúng phân bổ category: factual 6,
concept_explanation 5, code_behavior 7, multi_chunk 5, confusable 4 và
out_of_scope 3.

### 2. Candidate evidence package

`scripts/evaluation/locate_draft_evidence.py` được mở rộng bằng `--draft-file`
để dùng lại locator cho Batch 02 mà không đổi default Batch 01. Package
`evaluation/review/batch_02/candidates/batch_02_source_candidates_with_transcript_2026-08-01.csv`
có 138 dòng: 27 answerable draft × Top 5 (135) và ba out-of-scope (3).

Validation đã kiểm tra ID/rank, score order, target video, segment range,
timestamp và transcript excerpt khớp Silver. Package chỉ là candidate evidence,
không phải Ground Truth.

### 3. Human candidate decision record

Đã đọc workbook `evaluation/review/batch_02/decisions/batch_02_source_candidates_review_vi_translated.xlsx`
và lưu record có thể audit trong `evaluation/review/batch_02/BATCH_02_CONTENT_REVIEW.md`.
Sau chuẩn hóa case, workbook có 43 candidate `Được duyệt`, 36 `Mơ hồ` và 56
`Sai`; 23/27 câu answerable có ít nhất một candidate được duyệt. q-015, q-020,
q-025 và q-032 chưa có candidate được duyệt.

q-042 đến q-044 giữ out-of-scope theo draft/candidate status. Cột
`review_decision` của ba dòng này chứa literal `43`, không thuộc giá trị review
hợp lệ, nên không được dùng làm decision.

### 4. Tổ chức lại evaluation workspace

Đã nhóm artifact review theo `evaluation/review/batch_01/` và
`evaluation/review/batch_02/`, tách `candidates/` khỏi `decisions/`. Hai workbook
human review được copy vào `decisions/` trong project. Coverage Matrix chuyển vào
`evaluation/coverage/`. Markdown chỉ tham chiếu path bên trong project, không còn
tham chiếu thư mục ngoài workspace.

## Ranh giới chưa làm

* Không tạo Answer Points.
* Không đổi Batch 02 draft sang canonical JSONL hoặc `approved`.
* Không tự chọn final source range khi một question có nhiều candidate
  `Được duyệt`.
* Không chạy Hybrid Search, Cross-Encoder, LLM runtime hoặc retrieval metrics.

## Bước tiếp theo

Theo quyết định user ngày 2026-08-03, không quay lại vòng tạo candidate package
rồi human review cho Batch 02. Canonicalization chỉ có thể bắt đầu sau khi có
chỉ dẫn chọn final range cho những question có nhiều candidate được duyệt; q-015,
q-020, q-025 và q-032 cũng cần quyết định xử lý riêng mà không suy diễn từ
candidate hiện có.

---

# Ngày 19 - Batch 02 Evidence Selection và Validation

## Đã hoàn thành

### 1. Human evidence-role selection

Workbook `evaluation/review/batch_02/decisions/batch_02_source_candidates_review_benchmark.xlsx`
đã ghi vai trò evidence cho toàn bộ 138 dòng review: 23 `Primary`, 15
`Supporting`, 5 `Redundant`, 36 `Weak` và 59 `Rejected`. Mỗi trong 23 câu
answerable có evidence sẵn sàng có đúng một `Primary`; `Supporting` chỉ giữ lại
khi cần thêm range.

### 2. Final evidence selection manifest

Đã tạo
`evaluation/review/batch_02/decisions/batch_02_final_evidence_selection_2026-08-03.csv`.
Manifest có 30 dòng: 23 `selected`, bốn `unresolved_no_primary` (q-015, q-020,
q-025, q-032) và ba `out_of_scope` (q-042 đến q-044). Nó ghi rõ Primary,
Supporting, candidate rank, video ID, source segment và time range; tổng là 38
range được chọn.

### 3. Cross-file validation

Đã đối chiếu draft, candidate package, workbook evidence-role và manifest. Mọi
range được chọn khớp candidate/video/time/segment, có decision `Được duyệt`, có
time range `end_second > start_second` và segment range hợp lệ. Không có duplicate
question ID hoặc duplicate selected rank trong một question.

Ba dòng q-042 đến q-044 trong workbook evidence-role có `candidate_rank` và
`review_decision` bằng literal `43`, trong khi candidate package đánh dấu
`not_applicable_out_of_scope`. Đây là cảnh báo cấu trúc workbook; không có range
nào từ ba dòng này được chọn, và manifest giữ đúng out-of-scope với evidence rỗng.

## Ranh giới chưa làm

* Không tạo candidate Answer Points.
* Không đổi Batch 02 draft sang canonical JSONL, `approved` hoặc Ground Truth.
* Không xử lý hoặc thay evidence cho q-015, q-020, q-025, q-032.
* Không chạy Hybrid Search, Cross-Encoder, LLM runtime hoặc retrieval metrics.

## Bước tiếp theo

Chờ phê duyệt rõ trước khi tạo candidate Answer Points cho 23 câu có Primary và
canonicalize chúng. Bốn câu chưa có Primary cần evidence hoặc quyết định riêng;
q-042 đến q-044 tiếp tục giữ out-of-scope.

---

# Ngày 20 - Batch 02 Answer Points Review và Canonicalization

## Đã hoàn thành

### 1. Candidate Answer Points package

Đã tạo workbook
`evaluation/review/batch_02/answer_points/batch_02_candidate_answer_points_review_2026-08-10.xlsx`
từ final evidence selection. Package có 26 record: 22 `candidate_ready`, q-028
`blocked_evidence_not_entailing` và ba câu q-042 đến q-044 `out_of_scope`.
q-015, q-020, q-025 và q-032 không có Primary nên không được đưa vào package.

Candidate Answer Points chỉ dùng nội dung được selected transcript hỗ trợ. q-028
không được tạo Answer Points vì evidence đã chọn chỉ nói về debugging unexpected
output, không nói assertion failure.

### 2. Human Answer Points review

Workbook reviewed được lưu tại
`evaluation/review/batch_02/answer_points/batch_02_candidate_answer_points_review_2026-08-10_reviewed.xlsx`.
Kết quả có 19 `Accept`, ba `Reject` và một `Rewrite`; ba out-of-scope để trống.

Các câu bị Reject là q-024, q-028 và q-036 vì selected evidence không trả lời đủ
question intent. q-038 được Rewrite thành hai Answer Points bám selected evidence
về sorted-input requirement của bisection search và linear search.

Validation xác nhận 23/23 câu answerable trong workbook có quyết định hợp lệ, các
câu Reject có reviewer note, q-038 có bản EN/VI đầy đủ và phần question/evidence/
Machine Data không bị thay đổi so với workbook gốc.

### 3. Canonical Batch 02 subset

Đã thêm 20 record Batch 02 đạt review vào
`evaluation/mit_60001/evaluation_questions.jsonl`: 19 record dùng candidate Answer
Points được Accept và q-038 dùng reviewer Answer Points đã Rewrite. Tất cả record
mới có `review_status=approved`, reviewer `human_batch_02_2026-08-10`, relevant
video IDs và exact selected time ranges.

Canonical dataset sau khi cập nhật:

```text
Total approved records : 33
Answerable approved    : 31
Out-of-scope approved  : 2
Batch 01 records       : 13
Batch 02 records       : 20
Duplicate IDs          : 0
Validation errors      : 0
```

Coverage Matrix đã được cập nhật để tách Batch 02 approved khỏi các câu chưa
canonical.

## Ranh giới chưa làm

* Không canonicalize q-024, q-028, q-036 do human decision `Reject`.
* Không xử lý q-015, q-020, q-025, q-032 vì chưa có Primary evidence.
* Không canonicalize q-042 đến q-044 vì chưa có quyết định canonical cho các câu
  out-of-scope này.
* q-011 của Batch 01 vẫn chưa có canonical record.
* Chưa chạy retrieval comparison, build Gold full, Hybrid Search, Cross-Encoder,
  LLM runtime hoặc Search API.

## Bước tiếp theo

Benchmark hiện có 33 record approved và còn thiếu ít nhất bảy record để đạt ngưỡng
tối thiểu 40. Cần xử lý evidence/rewrite cho các câu chưa canonical hoặc bổ sung
câu mới có coverage phù hợp, sau đó mới chạy retrieval comparison ba chunking
configuration và chọn configuration cho Gold full.

---

# Ngày 21 - Batch 02 Completion Review và đạt ngưỡng 40 câu

## Đã hoàn thành

### 1. Completion evidence package

Đã tạo workbook
`evaluation/review/batch_02/completion/batch_02_completion_review_2026-08-11_reviewed.xlsx`
cho bảy câu chưa canonical. Bốn câu answerable q-015, q-020, q-025 và q-032 có
candidate Answer Points cùng sáu evidence range được tìm lại từ full Silver; ba câu
q-042 đến q-044 giữ vai trò out-of-scope với Answer Points và evidence rỗng.

q-020 được đề xuất rewrite từ câu hỏi rộng về string operations thành câu hỏi giới
hạn vào `len`, indexing và slicing. Hai evidence range của q-020 lần lượt hỗ trợ
`len`/indexing và slicing.

### 2. Human completion review

Human review có sáu quyết định `Accept` và một `Rewrite`. q-015, q-025, q-032,
q-042, q-043 và q-044 được Accept. q-020 được Rewrite với đầy đủ question EN/VI,
Answer Points EN/VI và reviewer note giải thích việc thu hẹp intent.

Validation workbook xác nhận 7/7 câu có quyết định hợp lệ, sáu evidence range khớp
Silver transcript, các out-of-scope payload vẫn rỗng và không có lỗi công thức.

### 3. Canonicalization và coverage

Đã thêm bảy record vào `evaluation/mit_60001/evaluation_questions.jsonl` với
reviewer `human_batch_02_2026-08-11`: bốn answerable record có Answer Points và
exact evidence range, ba out-of-scope record không gắn corpus evidence.

Canonical dataset sau khi cập nhật:

```text
Total approved records : 40
Answerable approved    : 35
Out-of-scope approved  : 5
Batch 01 records       : 13
Batch 02 records       : 27
Duplicate IDs          : 0
Validation errors      : 0
```

Coverage Matrix đã chuyển q-015, q-020, q-025, q-032 và q-042 đến q-044 sang
approved. Benchmark đã đạt ngưỡng tối thiểu 40 câu trong mục tiêu 40–60.

## Ranh giới chưa làm

* Không canonicalize q-024, q-028 và q-036 do human decision `Reject`.
* q-011 của Batch 01 vẫn chưa có canonical record.
* Chưa chạy retrieval comparison hoặc chọn chunking configuration.
* Chưa build Gold full, embedding, vector index, Hybrid Search, Cross-Encoder,
  LLM runtime hoặc Search API.

## Bước tiếp theo

Dùng cùng 40 record `approved` để chạy retrieval comparison cho ba chunking
configuration đã chốt. Sau khi đối chiếu metrics và evidence review contract mới
chọn configuration để build Gold full cho 38 video.

---

# Ngày 22 - Full Chunking Retrieval Comparison và Configuration Decision

## Đã hoàn thành

### 1. Full-corpus chunk candidates

Đã build ba candidate configuration trên đủ 38 MIT 6.0001 video từ 12.518 Silver
segments:

```text
fixed_wp240_o48_v1              : 548 chunks
semantic_cosine_wp240_v1        : 861 chunks
semantic_cosine_wp192_o32_v1    : 1.056 chunks
```

Cả ba pass schema validation, 38-video/source-segment coverage, timing/lineage,
duplicate check, non-tail undersize check và cross-process byte determinism. Sample
baseline hash không thay đổi.

### 2. Dense retrieval comparison

Dense cosine retrieval dùng `sentence-transformers/all-MiniLM-L6-v2`, revision
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, cho cùng 35 canonical question
`approved`, `answerable=true`. Năm câu out-of-scope không tham gia metrics. Ground
Truth relevance dùng cùng video và giao nhau theo Silver source-segment interval.

Kết quả chính:

| Configuration | MRR | Recall@1 | Recall@3 | Recall@5 | Recall@10 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `fixed_wp240_o48_v1` | 0,6503 | 0,4857 | 0,7429 | 0,8571 | 0,9714 |
| `semantic_cosine_wp240_v1` | 0,5736 | 0,3714 | 0,7429 | 0,8571 | 0,9143 |
| `semantic_cosine_wp192_o32_v1` | 0,5930 | 0,4286 | 0,7429 | 0,9143 | 0,9714 |

Retrieval detail, comparison và run manifest byte-identical qua hai Python process.
Manifest khóa evaluation/Silver/chunk hashes, model revision, normalization, relevance
rule và ranking tie-break.

### 3. Human citation review, re-audit và quyết định

Human review cuối cùng nằm tại
`evaluation/review/chunking/mit_60001_chunking_citation_review_2026-08-11_reaudited.xlsx`.
Re-audit đủ 35 câu ghi nhận:

| Configuration | Correct | Partial | Incorrect | Boundary Good | Preferred |
| --- | ---: | ---: | ---: | ---: | ---: |
| `fixed_wp240_o48_v1` | 28 | 6 | 1 | 4 | 4 |
| `semantic_cosine_wp240_v1` | 28 | 7 | 0 | 24 | 16 |
| `semantic_cosine_wp192_o32_v1` | 25 | 10 | 0 | 20 | 14 |

Có một câu `Tie`. Validation xác nhận 35 unique question ID, cùng question set giữa
ba configuration, không thiếu decision, không có giá trị ngoài review contract,
không có lỗi công thức và `Final_decision` khớp ba sheet nguồn.

User approve `semantic_cosine_wp240_v1` ngày 2026-08-12. Quyết định được lưu tại
`evaluation/review/chunking/mit_60001_chunking_configuration_decision_2026-08-12.csv`.
Artifact ghi retrieval run ID, hash workbook reaudited, automatic metrics, human
counts và selected status cho cả ba configuration.

Raw `reports/08_chunking/chunking_comparison.csv` không bị sửa tay vì đây là output
deterministic đã khóa bằng cross-process hash. Decision CSV là nguồn audit cho trạng
thái human review và configuration được chọn.

### 4. Canonical Gold full

Đã promote selected candidate thành
`data/gold/mit_60001/chunks.jsonl` bằng
`scripts/chunking/promote_selected_config.py`. Promotion đọc winner trực tiếp từ
decision CSV, kiểm tra hash workbook reaudited, full validation và full cross-process
report trước khi ghi canonical output.

Kết quả:

```text
Configuration      : semantic_cosine_wp240_v1
Chunks             : 861
Videos             : 38/38
Silver coverage    : 12.518/12.518 segments
Coverage missing   : 0
Coverage extra     : 0
Duplicate IDs      : 0
Schema errors      : 0
Validation errors  : 0
SHA-256            : c03abf002c29b784d191eb393670da27b80fed8e0e18798f113d7ff8b7daf432
```

Canonical output byte-identical với selected candidate. Validator kiểm lại schema,
selected config ID, Silver metadata, source range/count, lossless chunk text, timing,
lineage, content hash, chunk ID/index continuity và full segment coverage.

`scripts/chunking/verify_canonical_gold_cross_process.py` chạy promotion trong hai
Python processes. Canonical JSONL, manifest và validation CSV có SHA-256 giống nhau
giữa hai lần chạy. Canonical JSONL là generated data bị gitignore; manifest và hai
validation reports được giữ để audit.

## Ranh giới chưa làm

* Chưa tạo embedding hoặc vector index.
* Chưa xây Hybrid Search, Cross-Encoder, LLM runtime hoặc Search API.
* Chưa đánh giá answer groundedness hoặc abstention accuracy end-to-end.

## Bước tiếp theo

Thiết kế embedding/index từ canonical Gold full. Khóa model revision, dimension,
normalization, batch policy, canonical input hash và index output hash trước khi chạy
Hybrid Search hoặc Cross-Encoder.

---

# Ngày 23 - Canonical Embedding Index và Production Retrieval Validation

## Đã hoàn thành

### 1. Kiểm tra đầu vào và quyết định index MVP

Canonical Gold được kiểm lại trước khi encode: SHA-256
`c03abf002c29b784d191eb393670da27b80fed8e0e18798f113d7ff8b7daf432`, 861 record,
861 unique chunk ID, 38 video, chỉ có configuration `semantic_cosine_wp240_v1` và
không có `chunk_text` rỗng.

Index MVP dùng `sentence-transformers/all-MiniLM-L6-v2`, revision
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, 384 chiều, float32, L2-normalized và
exact cosine qua NumPy. Đây là production baseline v1 trên corpus 861 chunks, không
phải tuyên bố model tốt nhất cho mọi corpus.

### 2. Build canonical embedding/index

Đã thêm `scripts/embedding/build_mit_60001_index.py`. Builder khóa canonical input
hash, scope, count, selected config, model revision và dimension trước khi encode.
Generated output nằm tại `data/indexes/mit_60001/` và bị gitignore.

Kết quả:

```text
Index run ID       : mit60001_index_558e4d6e873847dd
Chunks             : 861
Unique chunk IDs   : 861
Videos             : 38
Embedding shape    : 861 x 384
Embedding dtype    : float32
Minimum norm       : 0,999999881
Maximum norm       : 1,000000119
Non-finite values  : 0
Zero-norm vectors  : 0
Norm violations    : 0
Embeddings SHA-256 : 3cf94fd32adf78e1e294d5562910f0d7144744a4c310de30f74f0084c80e56a7
Metadata SHA-256   : 376faf54d90b6c4a30dc562aeba2127cbdd2953c243cd341bc288068dce4c7d7
Index content hash : 6e78f39257b7cc5defebd6740aab2dc1a4c202165b073f7a740ee5a5d7c46805
Validation status  : passed
```

Manifest schema khóa model/revision, dimension, normalization, paths, counts, runtime
versions, input/output hashes và vector validation invariants.

### 3. Cross-process và production retrieval validation

`scripts/embedding/verify_index_cross_process.py` rebuild index trong hai Python
processes độc lập với cùng timestamp đã khóa. `embeddings.npy`, `metadata.jsonl`,
manifest và validation CSV có SHA-256 giống nhau giữa hai lần chạy.

`scripts/embedding/evaluate_index_retrieval.py` truy vấn production index bằng đúng
35 canonical answerable questions và 57 Ground Truth ranges. Năm out-of-scope
questions không tham gia Recall/MRR.

Kết quả:

| Metric | Production index |
| --- | ---: |
| MRR | 0,573585434 |
| Recall@1 | 0,371428571 |
| Recall@3 | 0,742857143 |
| Recall@5 | 0,857142857 |
| Recall@10 | 0,914285714 |

Toàn bộ metrics khớp selected-config dense baseline. Top 10 chunk IDs khớp 35/35
câu và Top 10 scores khớp 35/35 câu. Retrieval detail, comparison và run manifest
byte-identical qua hai Python processes.

### 4. Tài liệu trạng thái

Đã cập nhật `docs/status/CURRENT_STATUS.md`, implementation plan, schema README và
`reports/09_embedding/README.md` để ghi nhận Phase 6 hoàn thành.

## Ranh giới chưa làm

* Chưa xây lexical retrieval hoặc Hybrid Search.
* Chưa đánh giá hoặc tích hợp Cross-Encoder reranking.
* Chưa xây LLM accept/reject runtime, grounded answer generation hoặc Search API.
* Chưa đánh giá answer groundedness hoặc abstention accuracy end-to-end.
* Không đưa 286 transcript ngoài target vào index.

## Bước tiếp theo

Xây Hybrid Search trên cùng canonical Gold corpus và đánh giá bằng cùng 35 answerable
questions trước khi thêm Cross-Encoder hoặc Search API.

---

# Ngày 24 - Lexical/Hybrid Retrieval Comparison và Dense Selection

## Đã hoàn thành

### 1. Lexical design và exact BM25 index

Canonical Gold, dense embeddings và evaluation dataset được khóa lại bằng SHA-256
trước khi build. Tokenizer v1 giữ Python identifiers, dotted identifiers, số và
operators; không stemming hoặc stopword removal.

Exact BM25 index dùng `k1=1.2`, `b=0.75`, score float64 và cùng thứ tự 861 chunk IDs
với dense index. Kết quả:

```text
Lexical run ID       : mit60001_lexical_c8b5a0f1c77162b5
Documents            : 861
Unique chunk IDs     : 861
Videos               : 38
Vocabulary           : 3.334
Total tokens         : 102.223
Posting entries      : 57.804
Invalid positions    : 0
Invalid term freq    : 0
Duplicate postings   : 0
Lexical SHA-256      : 4fd1595a30ee85133bc6395d52278d2f5f2d9398c0c420d2c35031edb8e221f7
Validation status    : passed
```

Lexical index, manifest và validation report byte-identical qua hai Python processes.

### 2. Dense/BM25/RRF comparison

Ba method được đánh giá trên cùng 35 answerable questions và 57 Ground Truth ranges:

| Method | MRR | Recall@1 | Recall@3 | Recall@5 | Recall@10 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `dense_baseline_v1` | 0,573585434 | 0,371428571 | 0,742857143 | 0,857142857 | 0,914285714 |
| `bm25_v1` | 0,443842416 | 0,257142857 | 0,600000000 | 0,628571429 | 0,714285714 |
| `hybrid_rrf_k60_d100_v1` | 0,517862148 | 0,342857143 | 0,571428571 | 0,828571429 | 0,914285714 |

Equal-weight RRF cải thiện first relevant rank ở 12 câu, giữ nguyên 12 và làm xấu 11.
Full-evidence coverage rank cải thiện chín câu, giữ nguyên bảy và làm xấu 19. Dense
đúng nhưng Hybrid mất Recall@10 ở hai câu; Hybrid thêm hai câu khác nên aggregate
Recall@10 bằng nhau.

Dense branch khớp locked baseline ở toàn bộ metrics, Top 10 IDs 35/35 và Top 10
scores 35/35. Results, comparison, question comparison và manifest byte-identical
qua hai Python processes.

### 3. Retrieval configuration decision

User chọn `dense_baseline_v1` ngày 2026-08-14. `bm25_v1` và
`hybrid_rrf_k60_d100_v1` không được chọn vì thấp hơn Dense ở các metrics chính.
Decision artifact lưu tại
`reports/10_retrieval/retrieval_configuration_decision_2026-08-14.csv` và khóa hash
của comparison, question comparison và cross-process report.

Raw deterministic comparison không bị sửa; field `pending_human_decision` được giữ
nguyên và decision CSV riêng là nguồn trạng thái sau human review.

### 4. Tài liệu trạng thái

Đã cập nhật current status, implementation plan, schema README và
`reports/10_retrieval/README.md`.

## Ranh giới chưa làm

* Chưa thiết kế hoặc đánh giá Cross-Encoder reranking.
* Chưa khóa candidate depth và Top 3 evidence sau reranking.
* Chưa xây LLM accept/reject runtime, grounded answer generation hoặc Search API.
* Chưa đánh giá answer groundedness hoặc abstention accuracy end-to-end.
* Không đưa 286 transcript ngoài target vào retrieval corpus.

## Bước tiếp theo

Thiết kế Cross-Encoder experiment dùng candidates từ selected Dense baseline, sau đó
so sánh Top 3 reranked evidence với Dense Top 3 trên cùng 35 answerable questions.

---

# Ngày 25 - Cross-Encoder Evaluation và Dense Runtime Selection

## Đã hoàn thành

### 1. Khóa contract và chạy reranking

Dense Top 50 được chọn vì chứa first relevant và đầy đủ Ground Truth evidence cho
35/35 canonical answerable questions. Experiment chấm 1.750 question–chunk pairs
bằng `cross-encoder/ms-marco-MiniLM-L6-v2`, revision
`c5ee24cb16019beea0893ab7796b1df96625c6b8`, CPU, batch 16, max length 512 và raw
identity logits. Không có input bị truncate; input dài nhất là 214 tokens.

### 2. Kết quả và cross-process validation

| Method | MRR | Recall@1 | Recall@3 | Recall@5 | Recall@10 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `dense_baseline_v1` | 0,573585434 | 0,371428571 | 0,742857143 | 0,857142857 | 0,914285714 |
| `cross_encoder_ms_marco_minilm_l6_v2` | 0,532611871 | 0,342857143 | 0,657142857 | 0,771428571 | 0,914285714 |

First relevant rank của Cross-Encoder cải thiện tám câu, bằng nhau 11 và xấu hơn 16.
Full-evidence coverage rank cải thiện 12 câu, bằng nhau bốn và xấu hơn 19. Dense
metrics cùng Top 10 IDs/scores khớp locked baseline 35/35. Results, comparison,
question comparison, validation và manifest byte-identical với Python verification
process độc lập.

### 3. Human review và quyết định

Workbook review trong project chứa Dense Top 3 và Cross-Encoder Top 3 kèm 210 dòng
evidence text. Human review hoàn tất 35/35 câu và có notes cho mọi câu:

```text
Keep Dense          : 15
Use Cross-Encoder   : 13
Tie / Needs review  : 7
```

User chọn `dense_baseline_v1` ngày 2026-08-15. Decision CSV khóa hash workbook
reviewed, comparison, question comparison, manifest và cross-process report.
Cross-Encoder được giữ làm evaluated non-selected reranker, không nằm trong MVP
runtime path. Raw deterministic comparison tiếp tục giữ `pending_human_decision`.

q-023 và q-041 có human notes flag khả năng Ground Truth under-credit evidence hợp
lệ. Không sửa Ground Truth trong milestone này; nếu audit phải tạo review artifact
riêng.

### 4. Tài liệu trạng thái

Đã cập nhật current status, implementation plan, schema README và
`reports/11_reranking/README.md`.

## Ranh giới chưa làm

* Chưa xây Retrieval/Search API.
* Chưa xây LLM accept/reject runtime hoặc grounded answer generation.
* Chưa đánh giá answer groundedness hoặc abstention accuracy end-to-end.
* Chưa audit lại Ground Truth của q-023 và q-041.
* Không đưa 286 transcript ngoài target vào runtime corpus.

## Bước tiếp theo

Xây Retrieval/Search API dùng selected Dense baseline và trả Dense Top 3 evidence.
