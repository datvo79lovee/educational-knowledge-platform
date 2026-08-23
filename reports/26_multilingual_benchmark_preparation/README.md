# Phase 9 M1 — Multilingual benchmark preparation

## Scope

M1 chỉ chuẩn bị 20 semantic intents EN–VI và không chạy retrieval. Cả `question_en`,
`question_vi` và `literal_en` dùng nguyên Ground Truth của câu canonical tương ứng.

## Selection

Hai mươi câu được chọn có chủ đích từ 35 câu approved-answerable để phủ `what`,
`how`, `why`, `comparison`, `procedure`, `concept_relationship` và `multi_point`.
Selection cũng giữ cả intent có một Ground Truth range và intent có nhiều ranges.

## Translation contract

Translator local nhận duy nhất `question_vi`. Nó không nhận Ground Truth, expected
answer points, relevant chunk IDs, retrieved evidence hoặc answer labels.

```text
question_vi → Ollama llama3.2:3b → literal_en
```

Model digest và generation parameters được khóa trong M1 manifest. Bảy output draft
có drift rõ ràng đã được chạy lại sau khi làm rõ câu tiếng Việt; lịch sử trước/sau
được giữ trong `translation_revision_log_v1.jsonl`.

## Human review gate

Review từng dòng trong
`evaluation/review/multilingual/mit_60001_multilingual_m1_human_review.csv` bằng
đúng một trong ba nhãn:

- `Equivalent`
- `Minor wording difference`
- `Semantic drift`

Reviewer kiểm tra: `question_vi` tương đương `question_en`; `literal_en` giữ intent
của `question_vi`; và không có drift làm thay đổi Ground Truth. Nếu có
`Semantic drift`, phải sửa translation và review lại, không sửa Ground Truth.

## Final status

Human review hoàn thành 20/20 bởi Võ Trí Đạt ngày 2026-08-24:

- `Equivalent`: 19
- `Minor wording difference`: 1 (`mit60001-q-008`)
- `Semantic drift`: 0

Bản user-reviewed được giữ làm provenance và đã promote nguyên nội dung vào review
canonical. Artifact/manifest được rebuild sau review; M1 gate là `passed` và M1 đã
freeze. Chưa chạy retrieval trong M1.

```powershell
python -X utf8 scripts/evaluation/prepare_multilingual_benchmark_m1.py
python -X utf8 scripts/evaluation/validate_multilingual_benchmark_m1.py
```
