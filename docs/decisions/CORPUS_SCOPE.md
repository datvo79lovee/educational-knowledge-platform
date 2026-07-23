# Quyết định phạm vi corpus

## Trạng thái quyết định

Đã chấp nhận ngày 2026-07-13.

## Corpus mục tiêu

```text
Course: MIT 6.0001
Title: Introduction to Computer Science and Programming in Python
Term: Fall 2016
Playlist ID: PLUl4u3cNGP63WbdFxL8giv4yhgdMGaZNA
Playlist items: 38
```

## Baseline hiện tại

- Transcript đã có trong playlist: 4
- Playlist items chưa có trong corpus transcript: 34
- Coverage ban đầu: 4/38 = 10,53%

Bốn transcript hiện có:

| Position | Video ID | Title |
| ---: | --- | --- |
| 11 | `-jjUoTiaSHw` | String Manipulations |
| 24 | `-wz4iU2V-Yo` | Errors |
| 26 | `-DP1i2ZU9gk` | 8. Object Oriented Programming |
| 30 | `_ax4eNMI9Dw` | Method Call |

## Lý do chọn

- Một course cụ thể tạo phạm vi retrieval rõ ràng.
- Playlist có 38 items, đủ nhỏ để kiểm tra thủ công và đủ lớn cho MVP.
- Người phát triển có kiến thức Python để xây dựng câu hỏi và phát hiện câu trả lời
  sai hoặc không được nguồn hỗ trợ.
- Nội dung có trình tự, phù hợp để kiểm tra retrieval theo bài học.
- Targeted crawl tối đa 34 items, không cần quay lại 8.021 video của channel.

## Ranh giới corpus

### Trong scope

- Các video thuộc đúng playlist ID đã chốt.
- Transcript tiếng Anh khả dụng của các video đó.
- Metadata, segment timing và nguồn dẫn cần thiết để truy vết câu trả lời.
- Câu hỏi về nội dung được giảng trong MIT 6.0001 Fall 2016.

### Ngoài scope

- Video MIT 6.0001 từ học kỳ hoặc playlist khác.
- Các course Python khác.
- Tài liệu Python tổng quát ngoài playlist.
- 286 transcript hiện có nhưng không thuộc playlist mục tiêu.
- Câu hỏi về thư viện hoặc phiên bản Python không được course đề cập.

## Xử lý 286 transcript ngoài scope

Không xóa dữ liệu. Chúng vẫn nằm trong Bronze JSONL và PostgreSQL để phục vụ audit
hoặc mở rộng sau này. Target corpus được xác định bằng manifest riêng; chunking,
embedding, retrieval và evaluation của MVP chỉ đọc video ID trong manifest đó.

## Định nghĩa coverage

Không dùng duy nhất tỷ lệ `success / 38` vì một số video có thể không cung cấp
transcript.

Cần báo cáo hai chỉ số:

```text
playlist_coverage = successful_transcripts / 38
available_coverage = successful_transcripts / transcript_available_videos
```

Mục tiêu là lấy toàn bộ transcript tiếng Anh đang khả dụng. Video không có
transcript hoặc transcript bị tắt phải được ghi trạng thái, không retry vô hạn.

## Điều kiện thay đổi scope

Chỉ mở rộng scope khi pipeline và evaluation trên MIT 6.0001 đã hoàn tất. Mọi thay
đổi playlist hoặc thêm course phải tạo quyết định mới, không sửa ngầm manifest cũ.
