# Educational Knowledge Platform

## Nhật ký tiến độ - Ngày 1

Ngày: 17/06/2026

---

# Mục tiêu hoàn thành hôm nay

## 1. Thiết kế kiến trúc hệ thống

Đã hoàn thành:

* Architecture Diagram
* ERD Diagram

Luồng dữ liệu hiện tại:

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

## 2. Thiết kế mô hình dữ liệu

Đã thiết kế các bảng:

### sources

Lưu thông tin nguồn dữ liệu.

Ví dụ:

* MIT OpenCourseWare
* Stanford Online

### videos

Lưu metadata video:

* video_id
* title
* publish_date

### transcripts

Lưu transcript gốc của video.

### chunks

Lưu dữ liệu sau khi chunking.

---

## 3. Thiết lập môi trường phát triển

Hoàn thành:

* Cài đặt PostgreSQL
* Kết nối DataGrip
* Tạo database
* Kiểm tra kết nối thành công

Database:

educational_knowledge_platform

---

## 4. Xây dựng Schema

Đã tạo và triển khai:

sql/schema.sql

Các bảng đã được tạo thành công:

* sources
* videos
* transcripts
* chunks

Đã xác nhận các bảng tồn tại trong PostgreSQL.

---

## 5. Khởi tạo GitHub Repository

Hoàn thành:

* Git initialization
* GitHub remote connection
* Commit đầu tiên
* Push thành công lên GitHub

Các thành phần đã được quản lý bằng Git:

* README
* Documentation
* Architecture
* ERD
* Schema
* Source Code Structure

---

## 6. Cấu trúc dự án hiện tại

data/

* bronze/
* silver/
* gold/

docs/

* architecture.md
* architecture.png
* erd.png
* project_plan.md

sql/

* schema.sql

src/

* ingestion/
* processing/
* embedding/
* database/

---

# Các vấn đề gặp phải

## 1. Nhầm lẫn giữa schema.sql và PostgreSQL Schema

Đã hiểu rõ:

* schema.sql là file mã nguồn SQL
* PostgreSQL schema là đối tượng thực tế trong database

Bài học:

Mọi thay đổi cấu trúc database cần được lưu lại trong schema.sql để có thể tái tạo hệ thống.

---

# Kế hoạch ngày mai

## Mục tiêu chính

Xây dựng pipeline ingestion đầu tiên.

---

## Công việc 1

Thiết lập YouTube Data API v3

Bao gồm:

* Tạo Google Cloud Project
* Enable YouTube Data API
* Tạo API Key
* Lưu cấu hình vào file .env

Kết quả mong đợi:

Kết nối được tới YouTube API.

---

## Công việc 2

Xây dựng:

src/ingestion/fetch_videos.py

Chức năng:

* Kết nối YouTube API
* Lấy danh sách video từ MIT OpenCourseWare
* Trích xuất metadata

Các trường dữ liệu:

* video_id
* title
* publish_date

Kết quả mong đợi:

Thu thập được ít nhất 100 video.

---

## Công việc 3

Xây dựng:

src/database/load_videos.py

Chức năng:

* Đọc dữ liệu metadata
* Insert vào bảng videos

Kết quả mong đợi:

Bảng videos có trên 100 bản ghi.

---

# Tiêu chí hoàn thành ngày mai

Thành công nếu đạt được:

* Kết nối YouTube API
* Thu thập metadata video
* Insert dữ liệu vào PostgreSQL

Mục tiêu:

sources: 1

videos: 100+

# Nhật ký tiến độ - Ngày 2

Ngày: 18/06/2026

---

# Mục tiêu hoàn thành hôm nay

## 1. Thiết lập YouTube Data API

Đã hoàn thành:

- Tạo API Key
- Kết nối YouTube Data API v3
- Quản lý cấu hình bằng .env

Kết quả:

Kết nối thành công tới YouTube API.

---

## 2. Xây dựng Channel Discovery

Đã xây dựng:

src/ingestion/get_channel.py

Chức năng:

- Tìm kiếm kênh YouTube
- Lấy Channel ID

Kết quả:

MIT OpenCourseWare

Channel ID:

UCEBb1b_L6zDS3xTUrIALZOw

---

## 3. Xây dựng Uploads Playlist Discovery

Đã xây dựng:

src/ingestion/get_uploads_playlist.py

Chức năng:

- Truy vấn Channel API
- Lấy Uploads Playlist ID

Kết quả:

UUEBb1b_L6zDS3xTUrIALZOw

---

## 4. Xây dựng Ingestion Pagination Pipeline

Đã xây dựng:

src/ingestion/fetch_playlist_videos.py

Chức năng:

- Đọc Uploads Playlist
- Thực hiện pagination bằng nextPageToken
- Thu thập toàn bộ playlist items

Kết quả:

Total Records: 8021

Unique Video IDs: 8021

---

## 5. Xây dựng Bronze Layer đầu tiên

Đã hoàn thành:

data/bronze/videos_raw.jsonl

Định dạng:

JSON Lines (JSONL)

Mỗi dòng lưu một playlist item raw từ YouTube API.

Nguyên tắc:

Bronze lưu dữ liệu gần với nguồn nhất và không thực hiện deduplication.

---

# Kiến thức Data Engineering học được

## Pagination

Hiểu cơ chế:

nextPageToken

được sử dụng để truy xuất các trang dữ liệu tiếp theo cho đến khi giá trị trả về là None.

---

## Medallion Architecture

Bronze:

- Raw Data
- Có thể chứa duplicate
- Không xử lý nghiệp vụ

Silver:

- Clean Data
- Deduplicate
- Chuẩn hóa dữ liệu

Gold:

- Business Ready Data
---
## Vấn đề phát hiện

Ban đầu sử dụng:

youtube.search().list()

để thu thập video từ kênh MIT OpenCourseWare.

Kết quả:

Search API không phù hợp cho bài toán ingestion toàn bộ dữ liệu vì đây là API tìm kiếm, không phải API liệt kê toàn bộ nội dung của kênh.

Giải pháp:

Sử dụng:

Channel API
→ Uploads Playlist

PlaylistItems API
→ Pagination

để truy xuất toàn bộ video của kênh.
---

# Kế hoạch ngày tiếp theo

## Mục tiêu chính

Lấy metadata chi tiết cho toàn bộ video.

---

## Công việc 1

Xây dựng:

src/ingestion/fetch_video_metadata.py

Chức năng:

- Đọc danh sách video_id
- Gọi videos().list()

---

## Công việc 2

Thu thập:

- title
- description
- publish_date
- duration
- view_count

---

## Công việc 3

Lưu metadata vào Bronze Layer mới

Dự kiến:

data/bronze/video_metadata_raw.jsonl

---

# Tiêu chí hoàn thành

- Thu thập metadata chi tiết từ videos API
- Chuẩn bị dữ liệu cho Silver Layer
- Bắt đầu ánh xạ dữ liệu vào schema videos