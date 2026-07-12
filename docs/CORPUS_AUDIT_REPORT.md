# Báo cáo audit corpus hiện tại

## Ngày thực hiện

2026-07-12

## Phạm vi

Audit này chỉ đọc dữ liệu hiện có trong PostgreSQL và các file checkpoint. Không
crawl thêm dữ liệu, không sửa schema, không chunk và không embedding.

## Kết luận trực tiếp

290 transcript hiện tại hợp lệ về mặt kỹ thuật để chuyển sang bước phân tích
corpus. Tuy nhiên, chúng chỉ chiếm khoảng 3,62% trong tổng số 8.021 video của
channel. Vì chưa có quan hệ playlist và chưa có quy tắc chọn corpus rõ ràng, không
thể kết luận 290 transcript này đại diện cho MIT OpenCourseWare hoặc cho một nhóm
khóa học cụ thể.

Corpus hiện tại là một mẫu dữ liệu nhỏ lấy từ channel. Cho đến khi phân tích title,
description và playlist, không nên mô tả nó là một corpus khóa học có phạm vi rõ
ràng.

## Audit metadata video

- Nguồn dữ liệu: 1 (`MIT OpenCourseWare`)
- Tổng số video: 8.021
- Khoảng năm xuất bản: 2007–2026
- Số nhóm năm xuất bản: 20
- Video có duration: 8.020
- Video thiếu duration: 1
- Duration trung bình toàn bộ catalog: 2.435,26 giây

Metadata có một số duration cực lớn, bao gồm giá trị tối đa 62.937 giây. Các giá
trị này cần được xem là ngoại lệ để kiểm tra, không nên tự động coi là lỗi vì có
thể là video phát lại hoặc nội dung dài.

## Audit transcript đã nạp

- Transcript trong PostgreSQL: 290
- Transcript JOIN được với video: 290
- Transcript không JOIN được với video: 0
- Transcript có nội dung rỗng: 0
- Transcript thiếu duration video: 0
- Transcript thiếu description video: 1
- Ngôn ngữ lưu trong PostgreSQL: `en` = 290
- Độ dài nhỏ nhất: 439 ký tự
- Độ dài trung vị: 27.212,5 ký tự
- Độ dài lớn nhất: 101.387 ký tự
- Duration video nhỏ nhất: 41 giây
- Duration video trung bình: 2.369,83 giây
- Duration video lớn nhất: 7.554 giây

Video transcript thiếu description:

- `video_id`: `_GRVq26jIHs`
- Title: `2B. Intro 2: Biological Side of Computational Biology. Comparative Genomics, Models & Algorithms`
- Ngày xuất bản: 2022-08-22

## Phân bố độ dài transcript

| Khoảng độ dài | Số transcript |
| --- | ---: |
| Dưới 5.000 ký tự | 61 |
| Từ 5.000 đến dưới 20.000 | 64 |
| Từ 20.000 đến dưới 50.000 | 100 |
| Từ 50.000 trở lên | 65 |

Khoảng độ dài phân tán mạnh. Các transcript ngắn có thể là video giới thiệu, nội
dung ngắn hoặc transcript không đầy đủ. Chưa được phép loại chúng chỉ dựa trên độ
dài; cần kiểm tra theo title, duration và nội dung.

## Audit checkpoint

Checkpoint là file append-only, vì vậy phải tách số dòng lịch sử và trạng thái mới
nhất của mỗi video.

- Tổng số dòng lịch sử: 304
- Số `video_id` duy nhất: 302

| Trạng thái | Dòng lịch sử | Trạng thái mới nhất theo video |
| --- | ---: | ---: |
| `success` | 290 | 290 |
| `no_transcript` | 5 | 5 |
| `transcripts_disabled` | 5 | 5 |
| `fetch_failed` | 2 | 1 |
| `ip_blocked` | 2 | 1 |

Hai video lỗi được ghi hai lần nên tổng số dòng checkpoint lớn hơn số video duy
nhất. Khi báo cáo trạng thái hiện tại phải dùng cột “trạng thái mới nhất theo
video”, không dùng tổng số dòng lịch sử.

## Mức độ bao phủ

- Transcript thành công / toàn bộ catalog: 290 / 8.021, khoảng 3,62%
- Video đã xuất hiện trong checkpoint / toàn bộ catalog: 302 / 8.021, khoảng 3,77%
- Video chưa xuất hiện trong checkpoint: 7.719

Con số 7.719 không có nghĩa phải crawl toàn bộ số video này. Chưa có cơ sở để làm
việc đó. Trước tiên phải xác định corpus mục tiêu.

## File báo cáo

- `reports/video_summary.csv`: thống kê video theo năm và nguồn
- `reports/transcript_summary.csv`: chi tiết 290 transcript đã JOIN metadata
- `reports/checkpoint_status_summary.csv`: trạng thái lịch sử và trạng thái mới nhất
- `reports/video_transcript_summary.csv`: kết quả JOIN cơ bản đã tạo trước đó

## Quyết định chuyển bước

Có thể chuyển sang phân tích corpus vì 290 transcript đã qua kiểm tra kỹ thuật.
Bước tiếp theo phải trả lời các câu hỏi sau:

1. 290 video thuộc những course hoặc chuỗi bài giảng nào?
2. Chúng thuộc các domain kiến thức nào?
3. Có bao nhiêu video rời rạc không ghép được vào course?
4. Các transcript dưới 5.000 ký tự có phải dữ liệu không đầy đủ hay chỉ là video
   ngắn hợp lệ?

Chưa thực hiện playlist crawl trong bước audit này.
