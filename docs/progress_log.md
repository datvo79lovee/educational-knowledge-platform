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
