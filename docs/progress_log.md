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
