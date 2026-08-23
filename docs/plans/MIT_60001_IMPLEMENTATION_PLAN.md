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

## Bước tiếp theo — Multilingual Runtime Integration V1

Phase này chưa triển khai. Target flow:

```text
Vietnamese user query
  → original_query
  → literal English translator
  → retrieval_query
  → dense_baseline_v1 Top 3
  → G0 + answer_language=vi
  → Vietnamese answer + application-owned citations
```

Runtime contract cần thêm đúng ba khái niệm:

- `original_query`: câu người dùng nhập, giữ nguyên để answer generation hiểu ngôn
  ngữ và intent gốc.
- `retrieval_query`: literal English query dùng riêng cho Dense retrieval.
- `answer_language`: ngôn ngữ output, V1 là `vi` cho Vietnamese input.

Ranh giới: không sửa Dense/index/scoring, không thêm BM25/RRF/reranker và không dùng
Phase 9 để tune translator theo riêng `mit60001-q-008`.

## Engineering closeout sau Multilingual Runtime V1

Sau khi runtime multilingual được implement và validate: cập nhật demo, tài liệu
vận hành và cân nhắc Docker. Docker không nằm trong scope hiện tại.
