# Educational Knowledge Platform

# Ngày 1 - 17/06/2026

## 1. Mục tiêu trong ngày

* Thiết kế kiến trúc tổng thể dự án.
* Thiết kế mô hình dữ liệu.
* Thiết lập môi trường phát triển.
* Xây dựng schema PostgreSQL.
* Khởi tạo GitHub Repository.

---

## 2. Công việc đã thực hiện

### 2.1 Thiết kế kiến trúc hệ thống

Hoàn thành:

* Architecture Diagram.
* ERD Diagram.

Kiến trúc hiện tại:

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

PostgreSQL được sử dụng để lưu metadata và quản lý dữ liệu.

---

### 2.2 Thiết kế mô hình dữ liệu

Đã thiết kế các bảng:

#### sources

Lưu thông tin nguồn dữ liệu.

Ví dụ:

* MIT OpenCourseWare
* Stanford Online

#### videos

Lưu metadata video.

#### transcripts

Lưu transcript gốc.

#### chunks

Lưu dữ liệu sau khi chunking.

---

### 2.3 Thiết lập môi trường phát triển

Hoàn thành:

* Cài đặt PostgreSQL.
* Kết nối DataGrip.
* Tạo database.
* Kiểm tra kết nối thành công.

Database:

educational_knowledge_platform

---

### 2.4 Xây dựng Schema

Đã tạo:

sql/schema.sql

Các bảng:

* sources
* videos
* transcripts
* chunks

---

### 2.5 Khởi tạo GitHub Repository

Hoàn thành:

* Git initialization.
* GitHub remote connection.
* Commit đầu tiên.
* Push thành công lên GitHub.

---

## 3. Kết quả đạt được

* Hoàn thành thiết kế kiến trúc dự án.
* Hoàn thành ERD.
* Hoàn thành thiết kế schema database.
* Thiết lập thành công PostgreSQL.
* Khởi tạo GitHub Repository.

Dự án sẵn sàng chuyển sang giai đoạn triển khai ingestion pipeline.

---

## 4. Vấn đề gặp phải

### Vấn đề 1: Nhầm lẫn giữa schema.sql và PostgreSQL Schema

Ban đầu chưa phân biệt rõ:

* schema.sql (file mã nguồn SQL)
* PostgreSQL Schema (đối tượng trong database)

Sau khi tìm hiểu:

* schema.sql dùng để tái tạo cấu trúc database.
* PostgreSQL Schema là cấu trúc thực tế đang tồn tại trong DBMS.

---

## 5. Bài học rút ra

* Kiến trúc cần được thiết kế trước khi code pipeline.
* ERD giúp định hình luồng dữ liệu và schema.
* Mọi thay đổi database cần được lưu vào file SQL để có thể tái tạo hệ thống.

---

## 6. Trạng thái dự án

Đã hoàn thành:

* Architecture Diagram
* ERD Diagram
* PostgreSQL Setup
* Database Schema
* GitHub Repository

Chưa hoàn thành:

* YouTube API Integration
* Bronze Layer
* Silver Layer
* Gold Layer
* Embedding Pipeline

---

## 7. Kế hoạch ngày tiếp theo

### Mục tiêu

Xây dựng ingestion pipeline đầu tiên.

### Công việc

* Thiết lập YouTube Data API.
* Tìm hiểu cách lấy dữ liệu từ MIT OpenCourseWare.
* Thu thập video từ YouTube.
* Chuẩn bị dữ liệu cho Bronze Layer.

### Tiêu chí hoàn thành

* Kết nối được YouTube API.
* Thu thập được video từ MIT OpenCourseWare.
* Bắt đầu xây dựng ingestion pipeline.

---

# Ngày 2 - 18/06/2026

## 1. Mục tiêu trong ngày

* Kết nối YouTube Data API.
* Thu thập video từ MIT OpenCourseWare.
* Lưu dữ liệu vào Bronze Layer.
* Chuẩn bị metadata cho PostgreSQL.

---

## 2. Công việc đã thực hiện

### 2.1 Thiết lập YouTube Data API

Hoàn thành:

* Tạo API Key.
* Cấu hình file .env.
* Kết nối thành công YouTube Data API.

---

### 2.2 Tìm Channel ID

Đã xây dựng:

src/ingestion/get_channel.py

Kết quả:

MIT OpenCourseWare

↓

Channel ID:

UCEBb1b_L6zDS3xTUrIALZOw

---

### 2.3 Tìm Uploads Playlist

Đã xây dựng:

src/ingestion/get_uploads_playlist.py

Kết quả:

Uploads Playlist ID:

UUEBb1b_L6zDS3xTUrIALZOw

---

### 2.4 Xây dựng Pagination Pipeline

Đã xây dựng:

src/ingestion/fetch_playlist_videos.py

Chức năng:

* Đọc Uploads Playlist.
* Thu thập dữ liệu bằng pagination.
* Lặp cho tới khi nextPageToken bằng None.

Kết quả:

* Total Records: 8021
* Unique Video IDs: 8021

---

### 2.5 Xây dựng Bronze Layer đầu tiên

Đã lưu dữ liệu:

data/bronze/videos_raw.jsonl

Định dạng:

JSON Lines (JSONL)

Mỗi dòng lưu một playlist item raw từ YouTube API.

---

### 2.6 Quản lý mã nguồn

Đã tạo các commit:

* feat: lấy Channel ID từ kênh YouTube
* feat: lấy Uploads Playlist từ Channel ID
* feat: xây dựng pipeline phân trang thu thập video (pagination)
* chore: bổ sung gitignore cho data lake và môi trường
* docs: cập nhật kế hoạch dự án và tiến độ ngày 2

---

## 3. Kết quả đạt được

* Kết nối thành công YouTube Data API.
* Hiểu cách lấy dữ liệu từ một kênh YouTube.
* Thu thập thành công 8021 video từ MIT OpenCourseWare.
* Xây dựng ingestion pipeline đầu tiên.
* Xây dựng Bronze Layer đầu tiên của dự án.

---

## 4. Vấn đề gặp phải

### Vấn đề 1: Search API không phù hợp cho bài toán ingestion

Ban đầu sử dụng:

youtube.search().list()

Kỳ vọng:

* Lấy toàn bộ video của kênh MIT OpenCourseWare.

Kết quả:

* Không thể sử dụng Search API để thu thập toàn bộ dữ liệu của kênh.

Nguyên nhân:

* Search API được thiết kế cho bài toán tìm kiếm.
* Không phải API chuyên dụng để liệt kê toàn bộ video của một channel.

Giải pháp:

Channels API

↓

Uploads Playlist

↓

PlaylistItems API

↓

Pagination

---

### Vấn đề 2: Hiểu cơ chế Pagination

Ban đầu chưa hiểu vai trò của:

nextPageToken

Sau khi triển khai:

* Mỗi request trả về tối đa 50 video.
* nextPageToken dùng để truy xuất trang tiếp theo.
* Khi token trả về None nghĩa là đã đọc hết dữ liệu.

---

## 5. Bài học rút ra

* Không phải API nào trả dữ liệu cũng phù hợp cho ingestion.
* Cần hiểu mục đích thiết kế của từng API endpoint.
* Pagination là kỹ năng nền tảng trong Data Engineering.
* Bronze Layer nên lưu dữ liệu gần với nguồn nhất.
* JSONL phù hợp hơn JSON khi làm việc với dữ liệu lớn.

---

## 6. Trạng thái dự án

Đã hoàn thành:

* Architecture Diagram
* ERD Diagram
* PostgreSQL Setup
* Database Schema
* YouTube API Integration
* Channel Discovery
* Uploads Playlist Discovery
* Pagination Pipeline
* Bronze Layer Ingestion

Chưa hoàn thành:

* Video Metadata Enrichment
* PostgreSQL Data Loading
* Silver Layer
* Gold Layer
* Transcript Processing
* Embedding Pipeline
* Vector Database

---

## 7. Kế hoạch ngày tiếp theo

### Mục tiêu

Thu thập metadata chi tiết cho toàn bộ video.

### Công việc

Xây dựng:

src/ingestion/fetch_video_metadata.py

Sử dụng:

youtube.videos().list()

Thu thập:

* video_id
* title
* description
* publish_date
* duration
* view_count

Lưu dữ liệu:

data/bronze/video_metadata_raw.jsonl

### Tiêu chí hoàn thành

* Thu thập được metadata chi tiết của video.
* Chuẩn bị dữ liệu cho bảng videos.
* Sẵn sàng chuyển sang bước load dữ liệu vào PostgreSQL.
