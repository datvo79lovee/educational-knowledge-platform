# M6 provenance remediation

## Trạng thái

`REPRODUCTION HOÀN TẤT — CASE A`

M5 fresh-clone validation phát hiện SHA-256 worksheet được ghi trong original M6
manifests (`e9006c84160495873d8eac472678761452ec482554cc53c30cc7457f59ccc73a`)
không khớp worksheet blob đã commit tại M6 freeze commit
(`81da02c350de9daee685594be2bf07e780d917997795b1b19057b3d54c975967`).

Original M6 worksheet và manifests được giữ nguyên. P1 không tìm thấy byte
representation Git-reachable nào có recorded hash, vì vậy root cause là `UNKNOWN`.

### Quan sát forensic về worktree E

Trong `E:/educational-knowledge-platform`, worksheet worktree có SHA-256
`e9006c...` và `git ls-files -v` hiển thị tag `H`. Tag `H` viết hoa chỉ xác
nhận đây là tracked entry bình thường; nó không chứng minh `assume-unchanged`
và không giải thích vì sao discrepancy ở worktree E không xuất hiện trong
`git status`. Nguyên nhân vẫn là `UNKNOWN`. Reproduction chỉ dùng Git blob
canonical `81da02...` tại commit freeze.

## Reproduction đã đăng ký trước

`m6_provenance_preregistration.json` khóa freeze commit, source identities,
committed worksheet, aggregate projection, per-intent projection và luật Case A/B/C.
Validator mặc định chỉ kiểm tra preparation này bằng Git blobs tại commit freeze,
không đọc worksheet từ worktree E. Khi được truyền một checkout reproduction đã
được duyệt, validator trước hết xác nhận SHA worksheet, commit và source hashes;
nếu bất kỳ điều kiện nào lệch thì đó là Case C và evaluator không được chạy.

Reproduction dùng checkout tách biệt đúng tại `b7d1b1d`, worksheet canonical
`81da02...` và source đã pin. Frozen evaluator hoàn tất với `runtime_calls = 0`.
Validator báo `CASE A`: toàn bộ aggregate projection, 20/20 hàng projection theo
intent và G1–G4 khớp.

## Correction additive

Original M6 manifests và worksheet được giữ nguyên, kể cả recorded hash `e9006c...`.
`m6_provenance_correction.json` ghi sai lệch identity metadata với nguyên nhân
`UNKNOWN`; `m6_provenance_reproduction_result.json` ghi bằng chứng reproduction.
Do CASE A khớp toàn bộ projection đã preregister, kết quả M6 vẫn reproducible từ
artifact Git-canonical đã commit. Correction này không chứng minh production
readiness, generalization sang truy vấn mới, hoặc nguyên nhân tạo ra `e9006c...`.

## Ranh giới

- Không sửa `reports/35_multilingual_runtime_v1_m6/`.
- Không sửa original M6 runner hoặc freeze script.
- Không chạy lại model, human review hoặc Ground Truth.
- Không dùng original recorded hash làm reproduction input identity.
