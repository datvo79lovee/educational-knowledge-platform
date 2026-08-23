# Báo cáo playlist mapping

## Ngày thực hiện

2026-07-13

## Phạm vi

Thu thập public playlist metadata và playlist items của MIT OpenCourseWare để khôi
phục quan hệ giữa 290 video có transcript và playlist. Bước này không tải lại
transcript, không tải lại video metadata và không sửa PostgreSQL.

Uploads playlist bị loại khỏi phân tích vì nó đại diện cho toàn bộ video của
channel, không mang ý nghĩa course hoặc corpus selection.

## Kết quả

- Public curated playlists đã duyệt: 361
- Playlist đã checkpoint hoàn tất: 361
- Video transcript được kiểm tra: 290
- Quan hệ video–playlist: 284
- Video nằm trong ít nhất một playlist: 283
- Video không tìm thấy trong public playlist: 7
- Video nằm trong nhiều hơn một playlist: 1
- Cặp `video_id + playlist_id` trùng: 0
- Mapping có playlist ID không tồn tại trong danh mục: 0

Coverage playlist của corpus là 283/290, tương đương 97,59%.

## Quan hệ nhiều–nhiều

Chỉ một video xuất hiện trong hai public playlists:

```text
video_id: -qCEoqpwjf4
title: 6. Discrete Random Variables II
```

Playlists:

```text
MIT 6.041SC Probabilistic Systems Analysis and Applied Probability, Fall 2013
6.041 Probabilistic Systems Analysis and Applied Probability
```

Điều này xác nhận schema mapping phải hỗ trợ quan hệ nhiều–nhiều. Không được đặt
`playlist_id` trực tiếp như một thuộc tính duy nhất của video.

## Video không có public playlist mapping

| Video ID | Title | Course hiện tại |
| --- | --- | --- |
| `-X04WJoTDBc` | Linear Transformations | `18.06SC` |
| `-kkocTdn0iY` | Ted Carr Guest Lecture | `MAS.771` |
| `0-6a1SuihXM` | Powers of a Matrix | `18.06SC` |
| `_GT4SZibf5E` | Orthogonal Vectors and Subspaces | `18.06SC` |
| `_gsDTzOpiKo` | Lecture 19: Motor System, 1 | `9.01` |
| `_ozQJncmJYk` | Understanding Food – Creating Plots in R | `15.071` |
| `_qDdzzBDoPc` | Highlights for High School Guided Tour 2009 | `unresolved` |

Sáu trong bảy video vẫn có course code từ metadata. Chỉ video Guided Tour vừa
không có playlist vừa không xác định được course/domain.

Không được kết luận bảy video đã bị crawl sai. Playlist có thể đã bị xóa, chuyển
sang private, thay đổi membership hoặc video có thể được đăng riêng lẻ.

## Playlist có nhiều transcript match nhất

| Playlist | Tổng item | Transcript match |
| --- | ---: | ---: |
| MIT RES.6-012 Introduction to Probability, Spring 2018 | 266 | 11 |
| MIT 15.071 The Analytics Edge, Spring 2017 | 193 | 7 |
| MIT 8.01SC Classical Mechanics, Fall 2016 | 215 | 6 |
| MIT 8.06 Quantum Physics III, Spring 2018 | 100 | 6 |
| MIT 6.004 Computation Structures, Spring 2017 | 172 | 5 |
| MIT 6.0001 Introduction to Computer Science and Programming in Python | 38 | 4 |
| MIT 15.031J Energy Decisions, Markets, Policies | 21 | 4 |
| MIT 18.01SC Homework Help for Single Variable Calculus | 87 | 4 |
| MIT 6.042J Mathematics for Computer Science | 111 | 4 |
| MIT 7.012 Introduction to Biology | 35 | 4 |
| MIT 8.04 Quantum Physics I | 115 | 4 |

Số transcript match thấp hơn nhiều so với tổng item của playlist. Ví dụ,
`RES.6-012` có 11 transcript trong corpus nhưng playlist có 266 items. Điều này
xác nhận corpus hiện tại có coverage thấp ngay cả với các course xuất hiện nhiều
nhất.

## Playlist fallback cho course và domain

Trước playlist mapping:

- Course unresolved: 32
- Domain unresolved: 42

Sau khi chỉ dùng playlist title làm fallback khi metadata đang unresolved:

- Course unresolved: 25
- Domain unresolved: 38
- Course được playlist title bổ sung: 7
- Domain được playlist title bổ sung: 4

31/32 video chưa nhận diện course có playlist membership, nhưng chỉ 7 playlist
title chứa mã course đủ rõ cho rule hiện tại. “Có playlist” không đồng nghĩa “đã
xác định course”. Không ép nhãn cho 24 trường hợp còn lại.

## Cơ chế resume

Dữ liệu trung gian nằm tại:

```text
data/bronze/playlist_mapping/
```

Bao gồm cache playlist metadata, các mapping match và danh sách playlist đã hoàn
thành. Sau mỗi playlist, script ghi checkpoint. Nếu API hoặc tiến trình dừng, lần
chạy sau chỉ xử lý playlist chưa hoàn thành.

Cache thuộc Bronze và đang được `.gitignore` loại khỏi Git.

## File đầu ra

- `scripts/playlist_mapping/map_playlists.py`
- `reports/03_playlist_mapping/playlists.csv`
- `reports/03_playlist_mapping/video_playlist.csv`
- `reports/03_playlist_mapping/playlist_coverage.csv`
- `reports/03_playlist_mapping/playlist_distribution.csv`

## Quyết định tiếp theo

Không cần crawl lại toàn bộ channel. Playlist mapping đã chứng minh corpus hiện
tại rải trên nhiều course và coverage của từng playlist thấp.

Bước kế tiếp là chọn corpus mục tiêu. Phải chọn một hoặc một nhóm course cụ thể,
đặt tiêu chí coverage, rồi chỉ crawl bổ sung video thiếu trong các playlist đã
chọn. Chưa bắt đầu chunking trên toàn bộ 290 transcript.
