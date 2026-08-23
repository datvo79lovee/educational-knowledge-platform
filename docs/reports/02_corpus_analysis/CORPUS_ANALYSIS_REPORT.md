# Báo cáo phân tích corpus theo course và domain

## Ngày thực hiện

2026-07-13

## Phạm vi

Phân tích 290 transcript đã có trong PostgreSQL bằng title, description, mã course
MIT và metadata video. Bước này không gọi YouTube API, không crawl playlist, không
sửa database và không thực hiện chunking.

## Kết luận trực tiếp

290 transcript hiện tại là một corpus phân tán, không phải một tập khóa học có
phạm vi tập trung.

258 transcript có thể nhận diện mã course bằng bằng chứng rõ ràng trong metadata,
nhưng chúng trải trên 134 mã course. Trong số đó, 72 course chỉ có đúng 1
transcript. Course có nhiều transcript nhất chỉ chiếm 11/290, tương đương 3,79%
toàn bộ corpus.

Không nên tiếp tục mô tả 290 transcript này như một corpus hoàn chỉnh cho một
course, một ngành hoặc một chương trình học. Nó phù hợp để kiểm thử kỹ thuật tổng
quát, nhưng chưa phù hợp để đánh giá chất lượng semantic search theo một phạm vi
kiến thức cụ thể.

## Phương pháp nhận diện course

Script chỉ chấp nhận mã course khi mã xuất hiện cùng tiền tố `MIT` trong title
hoặc description. Ví dụ:

```text
MIT 6.0001 Introduction to Computer Science and Programming in Python
MIT 18.06SC Linear Algebra
MIT RES.6-012 Introduction to Probability
```

Các số hoặc chuỗi giống mã course nhưng không có bằng chứng `MIT` bị loại. Các
false positive đã phát hiện và loại gồm:

```text
fall-2004
DD.2.1
COVID-19
HS-002
```

Chuỗi trong URL như `ocw.mit.edu/RES-6-006S08` cũng không được tự động coi là bằng
chứng course trong bước này. Chúng sẽ được xử lý bằng playlist mapping hoặc quy
tắc URL riêng sau này.

## Kết quả nhận diện course

- Tổng transcript: 290
- Nhận diện được course code: 258
- Chưa nhận diện được course code: 32
- Số course code đã nhận diện: 134
- Course chỉ có 1 transcript: 72
- Course có ít nhất 4 transcript: 16
- Transcript nằm trong các course có ít nhất 4 transcript: 81

Các course có nhiều transcript nhất:

| Course code | Course name | Transcript |
| --- | --- | ---: |
| `RES.6-012` | Introduction to Probability | 11 |
| `15.071` | The Analytics Edge | 8 |
| `8.01` | Classical Mechanics | 6 |
| `8.06` | Quantum Physics III | 6 |
| `5.111` | Principles of Chemical Science | 5 |
| `6.004` | Computation Structures | 5 |
| `15.031J` | Energy Decisions, Markets, and Policies | 4 |
| `18.01SC` | Single Variable Calculus | 4 |
| `18.06SC` | Linear Algebra | 4 |
| `6.0001` | Introduction to Computer Science and Programming in Python | 4 |
| `6.042J` | Mathematics for Computer Science | 4 |
| `7.012` | Introduction to Biology | 4 |
| `8.04` | Quantum Physics I | 4 |
| `8.13` | Experimental Physics I & II | 4 |
| `9.04` | Sensory Systems | 4 |

Các con số trên không chứng minh coverage đầy đủ của bất kỳ course nào. Ví dụ,
course có 11 transcript vẫn có thể có nhiều video khác chưa được thu thập.

## Phân loại domain

Domain được suy ra bằng hai loại quy tắc:

1. Mã khoa MIT, ví dụ course `6.*` được gắn với nhóm Computer Science/Data.
2. Từ khóa trong course name và title khi không có mã khoa đủ rõ.

Đây là phân loại heuristic, không phải taxonomy chính thức của MIT.

| Domain | Transcript | Tỷ lệ |
| --- | ---: | ---: |
| Computer Science, AI và Data | 46 | 15,86% |
| Mathematics và Statistics | 45 | 15,52% |
| Physics | 44 | 15,17% |
| Chưa xác định | 42 | 14,48% |
| Engineering | 38 | 13,10% |
| Economics, Business và Management | 33 | 11,38% |
| Biology, Medicine và Neuroscience | 24 | 8,28% |
| Education, Communication và Media | 8 | 2,76% |
| Humanities và Social Science | 8 | 2,76% |
| Architecture và Urban Studies | 2 | 0,69% |

42 transcript chưa xác định domain không được ép vào nhóm gần nhất. Playlist và
course metadata cần được dùng để xử lý nhóm này.

## Kiểm tra 61 transcript dưới 5.000 ký tự

- Tổng số transcript dưới 5.000 ký tự: 61
- Duration nhỏ nhất: 41 giây
- Duration lớn nhất: 547 giây
- Duration trung bình: 241,69 giây
- Được đánh dấu `likely_valid_short_video`: 61
- Được đánh dấu `possible_incomplete`: 0

Rule `likely_valid_short_video` yêu cầu video không dài quá 600 giây và transcript
có ít nhất 2 ký tự cho mỗi giây video. Cả 61 transcript đều đạt rule này.

Kết luận: chưa có bằng chứng kỹ thuật cho thấy nhóm transcript ngắn bị cắt hoặc bị
thiếu. Chúng nhiều khả năng là transcript hợp lệ của video ngắn. Tuy nhiên, rule
này không thay thế manual review nội dung.

## Giới hạn

- Course extraction phụ thuộc metadata hiện có.
- Một video có thể thuộc nhiều playlist nhưng báo cáo hiện chỉ có một course code.
- Joint course như `6.046J / 18.410J` có thể chỉ giữ mã đầu tiên.
- Course name có thể khác nhau nhẹ giữa các video cũ và mới.
- Domain là nhóm nội bộ phục vụ audit, không phải phân loại chính thức.
- Chưa biết tổng số video thực tế của từng course nên chưa tính được course coverage.

## File đầu ra

- `scripts/corpus_analysis/analyze_corpus.py`: script phân tích chỉ đọc
- `reports/02_corpus_analysis/transcript_classification.csv`: phân loại từng transcript và bằng chứng
- `reports/02_corpus_analysis/course_distribution.csv`: phân bố theo course code
- `reports/02_corpus_analysis/transcript_distribution.csv`: phân bố theo domain
- `reports/02_corpus_analysis/short_transcript_review.csv`: danh sách 61 transcript ngắn

## Quyết định cho bước tiếp theo

Không crawl lại toàn bộ channel và không bắt đầu chunking.

Bước tiếp theo là crawl playlist metadata và playlist items để tạo mapping:

```text
video_id
→ playlist_id
→ playlist_title
```

Chỉ crawl quan hệ playlist. Không tải lại video metadata và không tải lại
transcript. Sau khi có mapping cần đo:

- bao nhiêu trong 290 video nằm trong playlist;
- mỗi video nằm trong bao nhiêu playlist;
- các course có ít transcript có thực sự thiếu coverage hay chỉ là video rời;
- 32 video chưa nhận diện course có được playlist giải thích hay không;
- 42 video chưa nhận diện domain có được playlist giải thích hay không.
