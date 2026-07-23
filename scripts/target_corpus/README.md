# MIT 6.0001 target corpus scripts

Folder này dành cho pipeline có scope cố định:

```text
MIT 6.0001 Introduction to Computer Science and Programming in Python
Fall 2016
PLUl4u3cNGP63WbdFxL8giv4yhgdMGaZNA
```

Các script dự kiến:

```text
build_target_inventory.py      implemented
fetch_target_transcripts.py    implemented
validate_target_corpus.py      planned
```

Inventory command:

```powershell
python scripts/target_corpus/build_target_inventory.py
```

The inventory step calls only the YouTube playlist-items endpoint. It does not
call the transcript API.

Target acquisition planning mode:

```powershell
python scripts/target_corpus/fetch_target_transcripts.py
```

Controlled test run:

```powershell
python scripts/target_corpus/fetch_target_transcripts.py --execute --limit 3 --min-delay 20 --max-delay 60
```

Without `--execute`, the script does not call the transcript API.

## Tham số của target crawler

| Tham số | Mặc định | Mục đích |
| --- | --- | --- |
| `--execute` | Tắt | Cho phép gọi transcript API và ghi Bronze/checkpoint. Không truyền thì chỉ planning. |
| `--video-id ID` | Không có | Chỉ chọn một video cụ thể. Có thể lặp lại tham số. ID phải thuộc manifest và gap candidates. |
| `--limit N` | Không giới hạn | Chỉ lấy N video đầu tiên của queue sau khi đã lọc scope và resume. Dùng để test nhỏ. |
| `--min-delay N` | `8` | Thời gian nghỉ tối thiểu giữa hai request, tính bằng giây. |
| `--max-delay N` | `20` | Thời gian nghỉ tối đa. Script chọn ngẫu nhiên trong khoảng min–max. |
| `--max-consecutive-failures N` | `5` | Dừng sau N lỗi retryable liên tiếp để tránh tiếp tục khi dịch vụ có vấn đề. |
| `--max-runtime-minutes N` | Không giới hạn | Dừng mềm sau N phút, giữ nguyên payload/checkpoint đã hoàn thành. |

### `--execute`

Đây là công tắc thay đổi dữ liệu. Khi không có tham số này, script vẫn validate
manifest, đọc Bronze/checkpoint, in queue và tạo report nhưng không request.

### `--video-id`

Dùng để test đúng video đã chọn, ví dụ:

```powershell
python scripts/target_corpus/fetch_target_transcripts.py `
  --execute `
  --video-id nykOeWgQcHM
```

Nếu ID nằm ngoài manifest hoặc đã có transcript, script dừng trước request. Với ID
bắt đầu bằng dấu `-`, dùng cú pháp `--video-id=-exampleId` để argparse không hiểu
nhầm ID là một option khác.

### `--limit`

`--limit 3` không có nghĩa lấy ba video bất kỳ. Script dựng queue hợp lệ theo
playlist position trước, bỏ qua payload/status đã hoàn thành, rồi mới lấy ba dòng
đầu tiên.

### Delay

Với `--min-delay 20 --max-delay 60`, khoảng nghỉ được chọn ngẫu nhiên từ 20 đến 60
giây sau mỗi request, trừ request cuối. Delay không bảo đảm tránh block nhưng làm
giảm nhịp request liên tục.

### Failure threshold và runtime

Lỗi cố định của riêng video như `no_transcript` không tăng bộ đếm lỗi liên tiếp.
Lỗi retryable như `fetch_failed` có tăng. Các lỗi block luôn dừng ngay, không chờ
đến threshold. Runtime limit được kiểm tra trước video tiếp theo nên không cắt giữa
lúc đang ghi một payload.

Không đặt crawler toàn channel trong folder này. Mọi script phải đọc target
manifest và từ chối video ID ngoài manifest.
