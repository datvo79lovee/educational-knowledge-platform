# Trạng thái hiện tại

## Ngày ghi nhận

2026-08-25

## Pipeline canonical

```text
YouTube API → Bronze → Silver → Gold
                         ↓
          lineage / hashes / schema validation / checkpoint-resume
                         ↓
             embedding / canonical Dense index
                         ↓
                  Dense Top 3 Search API
                         ↓
         G0 Grounded Answer Generator (llama3.2:3b)
                         ↓
      deterministic normalization → Pydantic validation
                         ↓
       application-owned citations → API response
```

## Corpus và benchmark

- Corpus mục tiêu: MIT 6.0001 Fall 2016, 38 video.
- Silver: 38/38 video, 12.518 segments.
- Canonical Gold: 861 chunks.
- Dense index: exact cosine, 861 × 384.
- Benchmark canonical: 40 câu approved; 35 answerable, 5 out-of-scope, 57 Ground
  Truth time ranges.
- Provenance benchmark được khóa tại
  `evaluation/mit_60001/benchmark_manifest.json`; validator kiểm tra schema,
  counts, reviewer-batch summary và SHA-256 của benchmark/schema.

## Retrieval và API

- Retriever canonical: `dense_baseline_v1`, Top 3 evidence.
- `POST /search` là retrieval-only.
- `POST /answer` gọi chính Dense Top 3, không gọi stage reviewer trung gian.
- Citation URL/timestamp do application dựng từ metadata của chunk; LLM không tự
  tạo citation.

## Grounded Answer G0 / Reliability V1

G0 là baseline canonical hiện tại, không phải production-ready claim.

| Metric | Kết quả |
| --- | ---: |
| Public runtime success | 40/40 |
| Decision accuracy | 23/37 = 62,16% |
| False abstain | 11/21 evidence-sufficient |
| False answer | 3/16 evidence-insufficient |
| Answer precision | 76,92% |
| Strict end-to-end | 17/37 = 45,95% |

Reliability normalization là behavior runtime có chủ đích: chỉ canonicalize literal
abstain thành `null` và deduplicate ID hợp lệ thuộc Dense Top 3. Pydantic vẫn là
final validator. Final metrics, results và manifest nằm tại
`reports/25_grounded_answer_reliability_v1/`; canonical human judgments nằm tại
`evaluation/review/grounded_answer/grounded_answer_reliability_v1_human_review_canonical.csv`.

## Thành phần đã loại

Evidence Reviewer, BM25, Hybrid RRF, Cross-Encoder và G1 prompt experiment không
còn code, test, report hoặc artifact trong working tree. Lý do chọn Dense/G0 được
tóm tắt tại `docs/decisions/CANONICAL_RUNTIME_DECISIONS.md`; Git history giữ lịch
sử development trước cleanup.

## Phase 9 — Multilingual Retrieval Baseline

Phase 9 đã complete và freeze trên 20 paired semantic intents. Ba representation
`question_en`, `question_vi` và frozen `literal_en` dùng cùng canonical Ground
Truth; human review M1 hoàn thành 20/20 với 19 `Equivalent`, 1
`Minor wording difference` (`mit60001-q-008`) và 0 `Semantic drift`.

M2 chạy đúng hai branches trên cùng `dense_baseline_v1`, canonical Gold/index và
full ranking 861:

```text
question_en → Dense
literal_en  → Dense
```

M2 có 40/40 retrieval records, 0 translator/LLM/generator call và deterministic
rerun PASS. M3 chỉ đọc frozen M1 + M2, không rerun retrieval hoặc sửa Ground Truth.

| Metric | EN canonical | VI → literal EN | Δ VI - EN |
| --- | ---: | ---: | ---: |
| MRR | 0,596274510 | 0,634226651 | +0,037952141 |
| Recall@1 | 0,400000000 | 0,550000000 | +0,150000000 |
| Recall@3 | 0,750000000 | 0,700000000 | -0,050000000 |
| Recall@5 | 0,800000000 | 0,750000000 | -0,050000000 |
| Full Evidence@3 | 0,500000000 | 0,550000000 | +0,050000000 |

First relevant rank có 4 intents improved, 10 unchanged và 6 degraded. Mean Top-3
overlap là 0,80; exact ordered Top-3 match là 6/20. Hai exact-string controls
`mit60001-q-003` và `mit60001-q-022` PASS.

Kết luận khóa: literal English translation preserved overall Dense retrieval
quality trên paired benchmark 20 intents, với mixed per-intent effects và không có
bằng chứng systematic degradation. Không diễn giải Vietnamese retrieval tốt hơn
English hoặc translation luôn làm retrieval kém đi.

Toàn bộ giảm 0,05 ở Recall@3/@5 đến từ `mit60001-q-008`, câu duy nhất có review
`Minor wording difference`: first relevant rank 2 → 7 và Top-3 overlap 0/3. Đây là
observed sensitivity về translation fidelity (`object` → `value`), không phải bằng
chứng cần fusion. Không sửa translation hậu nghiệm và không tune theo một failure
case đơn lẻ.

Quyết định sau M3: không mở `expanded_en`, query expansion, BM25, Hybrid RRF,
reranking hoặc model comparison. Phase 9 chuyển từ retrieval research sang runtime
integration.

## Multilingual Runtime V1 — M1 triển khai, M2 đo và bị từ chối

M1 đã triển khai nhánh runtime tiếng Việt:

```text
question_vi
  → literal translator (Ollama llama3.2:3b)
  → retrieval_query English
  → Dense Top 3
  → G0 + answer_language=vi
  → Vietnamese answer + application-owned citations
```

`POST /answer` nhận `answer_language: "en" | "vi"` và trả thêm `original_query`,
`retrieval_query`, `answer_language`. Nhánh English giữ prompt Reliability V1
**byte-identical** (`grounded_answer_prompt_v1`, sha `2b0a35d6…`) và không gọi
translator; nhánh VI dùng `grounded_answer_prompt_vi_v1` riêng và chưa có metric nào.
Translator lỗi thì runtime **fail-closed**, không âm thầm đem câu tiếng Việt đi Dense
retrieval.

M2 đo chính translator đã ship trên 20 paired intents của Phase 9, với gate và dự đoán
đăng ký trước khi chạy. Kết quả freeze tại `reports/30_multilingual_runtime_v1_m2/`:

```text
G1 semantic fidelity : FAIL   Semantic drift = 10/20, threshold = 0
G2 retrieval quality : FAIL   Recall@3 = 0,55, threshold = 0,65
Determinism          : FAIL   q-001 khác nhau giữa run A và run B
Overall              : FAILED
VI runtime candidate : REJECTED
```

| Nhánh | MRR | Recall@1 | Recall@3 | Recall@5 | Full Evidence@3 |
|---|---:|---:|---:|---:|---:|
| `question_en` | 0,596 | 0,40 | 0,75 | 0,80 | 0,50 |
| `literal_en` (người duyệt, frozen) | 0,634 | 0,55 | 0,70 | 0,75 | 0,55 |
| `machine_literal_en` | 0,497 | 0,40 | 0,55 | 0,65 | 0,40 |

Hai nhánh frozen tái lập chính xác baseline Phase 9, nên chênh lệch là thật. Human
adjudication: 4 `Equivalent`, 6 `Minor wording difference`, 10 `Semantic drift`. Bốn
dạng hỏng: xuất nhãn thay vì dịch (6 câu), trả lời thay vì dịch (2), đảo nghĩa (1),
sai thuật ngữ chuyên ngành (1). Không câu nào chạm trần `num_predict`, nên truncation
không phải nguyên nhân.

**Kết luận quan trọng nhất: retrieval metric có thể mù trước semantic translation
failure.** Bốn câu drift có `rank_delta = 0`; riêng `mit60001-q-039` mất hẳn vế
white-box nhưng Top-3 vẫn trùng `3/3` với bản dịch người. Nếu chỉ đặt gate retrieval,
kết luận sẽ sai. Gate dạng hội giữa metric tự động và phán đoán ngữ nghĩa của người là
thiết kế đúng, và M2 là bằng chứng thực nghiệm cho điều đó.

Determinism FAIL đo **riêng literal translator**. Nó cho thấy deterministic-rerun
guarantee của repository không thể mặc định suy rộng sang Ollama generation nói chung;
nó **không** phải kết luận về G0 English generator, vốn cần một test riêng.

## Multilingual Runtime V1 — M3 attempt 1 và M4 đo runtime failure

M3 attempt 1 chạy đúng runtime VI đã pin nhưng dừng ở intent thứ hai theo policy
stop-on-first-failure. `mit60001-q-002` phát sinh `GroundedAnswerContractError` vì
model trả `decision="abstain"` cùng answer khác `null`. Attempt chỉ có 2/20 record,
0 retry; G1 FAIL, còn G2–G4 `NOT_EVALUATED`. Attempt đã được freeze tại
`reports/31_multilingual_runtime_v1_m3/m3_final_manifest.json`. Không có kết luận
về answer correctness, groundedness, citation support hoặc parity tiếng Việt từ M3.

M4 thay **dụng cụ đo**, không thay runtime: đủ 20 paired intent được chạy với
continue-after-failure, 0 retry, atomic flush sau mỗi intent, capture raw generator
payload/translation query/Top 3 trên error path, và rehash runtime source sau
execution. Pre-registration R3 và execution artifacts đã được commit riêng.

| M4 runtime measurement | Kết quả |
| --- | ---: |
| Executed / passed / failed | 20 / 12 / 8 |
| Runtime failure rate | 8/20 = 0,400; Wilson 95% [0,219; 0,613] |
| Failure layer | `generation_contract`: 8; mọi layer khác: 0 |
| Retry | 0 |
| Integrity conditions I1–I4 | PASS |
| Raw payload, retrieval query, Top 3, generation telemetry trên failure | 8/8 captured |

Cả 8 failure có raw `decision="abstain"`; 12 record passed có `decision="answer"`.
Điều này mô tả runtime integrity trong **một execution sample**, không phải quality
metric, không phải parity với English baseline, và không phải tỉ lệ lỗi kỳ vọng vì
translator đã có bằng chứng non-determinism ở M2. Có hai dạng contract violation:
6 record `abstain` kèm answer khác `null`, 2 record `abstain` kèm
`supporting_chunk_ids` không rỗng. Không có translation/provider failure trong sample.

M4 không human-review và không tính quality metric. Giả thuyết prompt VI có tín hiệu
mâu thuẫn với abstention là hướng chẩn đoán tương lai, chưa phải kết luận nhân quả và
không được sửa trong M4.

## Multilingual Runtime V1 — M5.1 failed, M5.2 rollback và M5.3 runtime PASS

M5.1 thử đúng một prompt artifact candidate `grounded_answer_prompt_vi_v2` trên cùng
20 intent. Pre-registration revision 5 được commit trước execution. Attempt chạy đủ
20/20, zero retry: G1 PASS, G3 PASS nhưng G2 FAIL vì `mit60001-q-025` trả
`decision="abstain"`, `answer=null` và một supporting chunk. Kết quả 19 passed / 1
failed đã freeze tại `reports/33_multilingual_runtime_v1_m5/m5_1_final_manifest.json`;
candidate bị `REJECTED`.

M5.2 đã rollback prompt active về `grounded_answer_prompt_vi_v1`, khớp M4 source pin
`ac8541bea67a...`. Rollback không gọi model, không rerun M5.1 và không mở candidate
mới. Runtime VI active vẫn chưa production-ready vì prompt được restore chính là
runtime đã quan sát 8/20 failure ở M4.

M5.3 mở một candidate khác, không đổi prompt/model/translator/Dense: application chỉ
canonicalize một payload VI đã chọn `decision="abstain"` nhưng còn answer và/hoặc
supporting IDs hợp lệ thuộc Dense Top 3. Raw model payload vẫn được giữ để audit;
English, unknown ID, malformed type, empty-string answer và non-abstain không được
repair.

Attempt `m5-3-attempt-1` đã freeze tại
`reports/34_multilingual_runtime_v1_m5_3/m5_3_final_manifest.json`:

| M5.3 runtime gate | Kết quả |
| --- | ---: |
| Executed / passed / failed | 20 / 20 / 0 |
| Translation / retrieval / generation calls | 20 / 20 / 20 |
| Retry | 0 |
| VI abstain payload được canonicalize | 8 |
| G1 execution / G2 failure / G3 scope / G4 normalization | PASS / PASS / PASS / PASS |
| Runtime rehash sau execution | PASS, 0 mismatch |

M5.3 chỉ chứng minh runtime/normalization integrity trên attempt đã đăng ký trước.
Nó **không** chứng minh Vietnamese answer correctness, groundedness, citation support,
translation fidelity, parity với English, production readiness hoặc demo readiness.
Ví dụ raw output `q-033` vẫn dịch decomposition thành “nuclear fission”.

## Multilingual Runtime V1 — M6 human quality evaluation PASS

M6 đã đóng băng tại `reports/35_multilingual_runtime_v1_m6/m6_final_manifest.json`,
trạng thái `frozen_passed_quality_gates`. M6 đánh giá 20 output VI đã freeze tại M5.3
bằng một lượt human review mù (không thấy `retrieval_query`, raw model output,
normalization metadata, nhãn M2 hay outcome cũ), đúng 19 intent primary,
`mit60001-q-023` review mô tả nhưng loại khỏi metric do Ground Truth ambiguity đã
freeze từ Reliability V1.

| M6 gate | Ngưỡng | Quan sát | Kết quả |
| --- | --- | ---: | --- |
| G1 review integrity | 20/20 hợp lệ | 20/19/1 | PASS |
| G2 language compliance | 0 "Not Vietnamese" | 12/12 | PASS |
| G3 decision non-inferiority | ≥10/19 | 14/19 | PASS |
| G4 strict E2E non-inferiority | ≥6/19 | 7/19 | PASS |

Matched English reference (từ Reliability V1, cùng 19 intent): decision correct
11/19, strict E2E 7/19, strict answer 2/19. Strict answer success của VI là 1/19
(diagnostic only, không phải gate, vì reference tiếng Anh 2/19 quá thấp để làm gate
ổn định).

Kết luận được phép duy nhất: candidate M5.3 (không đổi) đã pass M6 quality gates trên
sample 19-record primary đã dùng lại nhiều lần. **Không** được suy ra production
readiness, tổng quát hóa sang query chưa thấy, quan hệ nhân quả giữa
translation/retrieval/generation và lỗi cuối, translator fidelity đã phục hồi, hay M2
(literal translator, vẫn `frozen_failed`) bị đảo ngược. M6 không mở lại M2.

## Bước tiếp theo

M6 PASS chỉ cho phép cân nhắc một milestone demo cục bộ có giới hạn (bounded local
demo), scope riêng, đăng ký trước riêng — chưa bắt đầu code demo. Không rerun M5.3
hay M6, không tune translator/prompt từ các record đã quan sát, không mở retrieval
experiment mới.
