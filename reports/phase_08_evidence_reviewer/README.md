# Phase 8 — Evidence Reviewer experiments (archived)

Folder này gom toàn bộ report của Phase 8 theo đúng thứ tự thực hiện:

| Stage folder | Nội dung |
|---|---|
| `13_evidence_review/` | Provider-independent request/calibration package |
| `14_evidence_review_runtime/` | Baseline Ollama reviewer runtime |
| `15_evidence_reviewer_evaluation/` | Baseline canonical evaluation |
| `16_evidence_reviewer_prompt_experiment/` | V1 control và Prompt V2 experiment |
| `17_evidence_reviewer_prompt_evaluation/` | Prompt V2 canonical evaluation |
| `18_evidence_reviewer_a1_experiment/` | A1 two-stage runtime/stability experiment |
| `19_evidence_reviewer_a1_evaluation/` | A1 canonical evaluation và final decision |

Evidence Reviewer đã bị loại khỏi active runtime architecture. Các folder này được
giữ nguyên để audit quyết định engineering; không tiếp tục V2.1, A1.1 hoặc A2 trong
scope project hiện tại.

## Frozen manifest compatibility

Các manifest đã khóa trước khi folder được gom vẫn giữ đường dẫn lịch sử dạng
`reports/13...` đến `reports/19...`. Không rewrite các manifest đó vì thay đổi byte
sẽ làm mất SHA-256 và experiment identity đã freeze.

Source code và validator hiện resolve các đường dẫn lịch sử này sang parent folder
`reports/phase_08_evidence_reviewer/`. Compatibility mapping chỉ thay đổi vị trí vật
lý; không thay nội dung artifact, metric hoặc run identity.

Active target pipeline hiện tại:

```text
Question
  -> Dense Top 3
  -> Grounded Answer Generator
       -> Answer + citations
       -> hoặc Abstain
```
