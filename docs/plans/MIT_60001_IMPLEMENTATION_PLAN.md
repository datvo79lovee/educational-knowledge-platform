# Kế hoạch triển khai MIT 6.0001

## Mục tiêu

Xây dựng project Data Engineering và NLP/RAG có thể tái lập: từ transcript YouTube
đến Dense retrieval, grounded local answer và citations có provenance.

## Phases đã hoàn thành

| Phase | Kết quả canonical |
| --- | --- |
| 1–4 | Target corpus, Bronze/Silver, PostgreSQL validation, cleaning và checkpoint/resume hoàn thành cho 38 video. |
| 5 | Chunking được đánh giá; 861 canonical Gold chunks được promote. |
| 6 | 861 × 384 exact Dense embedding/index được build và validate. |
| 7 | Dense Top 3 được chọn và Search API được validate. |
| 8 | G0/Reliability V1 Grounded Answer runtime và evaluation hoàn thành; deterministic normalization + Pydantic validation là canonical behavior. |
| 9 | Multilingual paired baseline M1–M3 hoàn thành: 20 intents, 40 full-rank Dense outputs, deterministic evaluation và quyết định không mở expanded translation/RRF. |
| Cleanup | Failed/deprecated retrieval, reviewer và prompt artifacts được loại; benchmark provenance được nén thành manifest có hash. |

## Quyết định architecture đã khóa

```text
Question → Dense Top 3 → G0 Grounded Answer Generator
                         ├─ answer + supporting chunk IDs + application citations
                         └─ abstain
```

- Không có Evidence Reviewer riêng.
- Không dùng BM25, Hybrid RRF hoặc Cross-Encoder trong runtime.
- Không mở thêm prompt tuning generator trên development set hiện tại.
- G0 là baseline evaluated; không tuyên bố production-ready.

## Phase 9 — Multilingual Retrieval Baseline — Complete

### Mục tiêu

Đo ảnh hưởng riêng của Vietnamese → literal English translation lên Dense retrieval
so với canonical English query trên cùng Ground Truth.

### Thiết kế khóa trước

```text
EN canonical query → dense_baseline_v1
VI query → literal English translation → dense_baseline_v1
```

- 20 paired semantic intents đã human review và freeze.
- Dùng nguyên canonical Gold/index và Ground Truth hiện có.
- Metrics: MRR, Recall@1, Recall@3, Recall@5, Full Evidence@3.
- M2 export full ranking 861 cho 20 EN + 20 frozen `literal_en` queries.
- Không dùng expanded translation, query expansion, fusion/RRF, model mới hoặc
  reranking.

### Kết quả M1–M3

1. M1: 20/20 paired intents reviewed; 19 `Equivalent`, 1 `Minor wording
   difference` (`mit60001-q-008`), 0 unresolved drift và 0 Ground Truth leakage.
2. M2: 40/40 retrieval records trên cùng canonical Dense/index, depth 861; exact
   controls và deterministic rerun PASS; không tính quality metrics.
3. M3: deterministic evaluation PASS, không rerun retrieval, sửa Ground Truth hoặc
   relabel.

| Metric | EN canonical | VI → literal EN | Δ VI - EN |
| --- | ---: | ---: | ---: |
| MRR | 0,596274510 | 0,634226651 | +0,037952141 |
| Recall@1 | 0,400000000 | 0,550000000 | +0,150000000 |
| Recall@3 | 0,750000000 | 0,700000000 | -0,050000000 |
| Recall@5 | 0,800000000 | 0,750000000 | -0,050000000 |
| Full Evidence@3 | 0,500000000 | 0,550000000 | +0,050000000 |

Paired first relevant rank: 4 improved, 10 unchanged, 6 degraded. Mean Top-3
overlap là 0,80 và exact Top-3 match 6/20. Literal translation giữ overall Dense
retrieval quality trên benchmark nhỏ này, với mixed per-intent effects và không có
bằng chứng systematic degradation.

### Quyết định khóa sau M3

- Không mở `expanded_en`, query expansion hoặc RRF.
- Không mở BM25, reranker, model comparison hoặc retrieval experiment mới.
- Không sửa `mit60001-q-008` hậu nghiệm. Giữ đây là limitation/observed
  sensitivity về translation fidelity: first relevant rank 2 → 7; toàn bộ giảm
  Recall@3/@5 aggregate đến từ intent này.
- Không tuyên bố Vietnamese retrieval tốt hơn English; kết quả chỉ hỗ trợ kết luận
  overall quality được giữ với mixed per-intent effects.

## Multilingual Runtime Integration V1 — M1–M6 hoàn thành

Runtime flow đã triển khai và pass quality gate tại M6:

```text
Vietnamese user query
  → original_query
  → literal English translator
  → retrieval_query
  → dense_baseline_v1 Top 3
  → G0 + answer_language=vi
  → Vietnamese answer + application-owned citations
```

`original_query`, `retrieval_query`, `answer_language` đã có trong contract. Dense
retrieval, index và scoring không đổi qua toàn bộ M1–M6; không có BM25/RRF/reranker.

Trạng thái từng milestone:

| Milestone | Nội dung | Kết quả |
| --- | --- | --- |
| M1 | Runtime nhánh VI: translator + `answer_language=vi` | Triển khai |
| M2 | Đo literal translator trên 20 paired intents | `frozen_failed`, translator REJECTED |
| M3 attempt 1 / M4 | Đo runtime failure rate trên output M5.3-tiền-thân | Đo, không gate |
| M5.1 | Candidate prompt `vi_v2` | `REJECTED`, G2 FAIL |
| M5.2 | Rollback prompt về `vi_v1` (khớp M4 pin) | Rollback, không candidate mới |
| M5.3 | Candidate application-boundary normalization cho abstain payload | `frozen_passed_runtime_gates`, ADVANCE_TO_M6 |
| M6 | Human quality evaluation trên output M5.3 đã freeze, 19-intent primary | `frozen_passed_quality_gates`, G1–G4 PASS |

Kết luận được phép sau M6: candidate M5.3 (không đổi) đã pass quality gates trên
sample 19-record primary đã dùng lại nhiều lần. Không production-ready, không tổng
quát hóa sang query chưa thấy, không quan hệ nhân quả với translation/retrieval/
generation, không phục hồi translator fidelity, không đảo ngược M2.

## Bước tiếp theo — Bounded local demo (chưa bắt đầu)

M6 PASS chỉ cho phép cân nhắc một milestone demo cục bộ có giới hạn (bounded local
demo), cần pre-registration và scope riêng. Chưa có code demo nào được viết. Ranh
giới giữ nguyên: không sửa Dense/index/scoring, không thêm BM25/RRF/reranker, không
tune translator/prompt theo output đã quan sát trong M1–M6.

## Engineering closeout sau bounded local demo

Sau khi demo cục bộ được implement và validate trong scope riêng: cập nhật tài liệu
vận hành và cân nhắc Docker. Docker không nằm trong scope hiện tại.
