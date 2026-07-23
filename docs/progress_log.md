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
