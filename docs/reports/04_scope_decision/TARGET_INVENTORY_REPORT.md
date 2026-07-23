# Báo cáo target inventory MIT 6.0001

## Ngày thực hiện

2026-07-13

## Phạm vi

Inventory playlist:

```text
MIT 6.0001 Introduction to Computer Science and Programming in Python
Fall 2016
Playlist ID: PLUl4u3cNGP63WbdFxL8giv4yhgdMGaZNA
Scope version: mit_60001_fall_2016_v1
```

Bước này chỉ gọi YouTube playlist-items endpoint và đọc PostgreSQL, Bronze JSONL,
checkpoint. Không gọi transcript API.

## Kết quả kiểm tra playlist

- Playlist items: 38
- Video ID duy nhất: 38
- Duplicate video ID: 0
- Position: liên tục từ 0 đến 37
- Video không tồn tại trong PostgreSQL: 0
- Duration nhỏ nhất: 50 giây
- Duration lớn nhất: 3.086 giây
- Duration trung bình: 944,68 giây

## Trạng thái transcript

| Trạng thái | Số video |
| --- | ---: |
| `already_available` | 4 |
| `not_attempted` | 34 |
| Trạng thái cố định không khả dụng | 0 |
| Lỗi retryable | 0 |
| Cần manual reconciliation | 0 |

34 video gap đều chưa từng được transcript pipeline thử xử lý. Chúng không phải
video đã thất bại, bị tắt transcript hoặc bị đánh dấu không có transcript.

## Bốn transcript hiện có

| Position | Video ID | Title | Duration |
| ---: | --- | --- | ---: |
| 11 | `-jjUoTiaSHw` | String Manipulations | 185 giây |
| 24 | `-wz4iU2V-Yo` | Errors | 76 giây |
| 26 | `-DP1i2ZU9gk` | 8. Object Oriented Programming | 2.504 giây |
| 30 | `_ax4eNMI9Dw` | Method Call | 107 giây |

## Target manifest

Manifest chứa đúng 38 video và được version bằng:

```text
mit_60001_fall_2016_v1
```

SHA-256 của manifest tại thời điểm tạo:

```text
f8f9108a3dc910219e2e915e83519c7054afc9c2783714b94ecdc145c150fda4
```

Script không ghi đè manifest nếu playlist hiện tại khác manifest v1. Khi scope
thay đổi phải tạo version mới.

## File đầu ra

- `reports/04_scope_decision/target_playlist_inventory.csv`: trạng thái chi tiết
  của đủ 38 video.
- `reports/04_scope_decision/target_gap_report.csv`: 34 video chưa có transcript.
- `reports/04_scope_decision/target_manifest.csv`: danh sách bất biến điều khiển
  downstream pipeline.

## Quyết định chuyển bước

Inventory hợp lệ. Có thể xây dựng targeted transcript acquisition chỉ cho 34 video
có `fetch_candidate=True`.

Crawler tiếp theo phải đọc manifest và gap report, từ chối video ngoài scope, hỗ
trợ checkpoint/resume và dừng khi gặp IP block. Chưa được giả định cả 34 video đều
có transcript khả dụng.
