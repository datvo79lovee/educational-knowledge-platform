# Educational Knowledge Platform

## Project Overview

Xây dựng hệ thống Data Engineering thu thập, xử lý và tìm kiếm nội dung giáo dục từ YouTube.

Nguồn dữ liệu ban đầu:

- MIT OpenCourseWare

Mục tiêu cuối cùng:

- Thu thập video metadata
- Thu thập transcript
- Xây dựng Data Lake theo Medallion Architecture
- Sinh embedding
- Lưu vector vào Vector Database
- Hỗ trợ semantic search

---

# Architecture

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

---

# Development Roadmap

## Phase 1 - Foundation

### Database

- [x] PostgreSQL setup
- [x] DataGrip connection
- [x] Schema design

### Documentation

- [x] Architecture Diagram
- [x] ERD Diagram

---

## Phase 2 - Ingestion

### YouTube API

- [x] API connection
- [x] Channel discovery
- [x] Uploads playlist discovery
- [x] Playlist pagination

### Bronze Layer

- [x] Playlist items ingestion
- [ ] Video metadata ingestion
- [ ] Transcript ingestion

---

## Phase 3 - Data Processing

### Silver Layer

- [ ] Data cleaning
- [ ] Deduplication
- [ ] Validation

### Gold Layer

- [ ] Topic classification
- [ ] Course aggregation
- [ ] Analytics datasets

---

## Phase 4 - Knowledge Retrieval

### Embedding

- [ ] Chunk generation
- [ ] Embedding generation

### Vector Database

- [ ] Vector storage
- [ ] Semantic search

---

# Current Status

Phase 2 - Ingestion

Completed:

- YouTube API integration
- Playlist pagination
- Bronze ingestion

Next milestone:

- Video metadata ingestion using videos().list()