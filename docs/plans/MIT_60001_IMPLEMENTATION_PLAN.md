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

## Phase 9 — Multilingual Retrieval Baseline

### Mục tiêu

Đo mức suy giảm retrieval của Vietnamese query khi literal-translate sang English,
so với English canonical query trên cùng benchmark.

### Thiết kế khóa trước

```text
EN canonical query → dense_baseline_v1
VI query → literal English translation → dense_baseline_v1
```

- Khoảng 20 paired semantic intents.
- Dùng nguyên canonical Gold/index và Ground Truth hiện có.
- Metrics: MRR, Recall@1, Recall@3, Recall@5, Full Evidence@3.
- Chưa thử expanded translation, query expansion, fusion/RRF, model mới hoặc
  reranking ở baseline này.

### Điều kiện hoàn thành

1. Paired intents và bản dịch literal được human review.
2. Mỗi run có manifest/hash và có thể chạy lặp lại.
3. Báo cáo tách rõ English baseline và Vietnamese translated result.
4. Chỉ mở experiment tiếp theo nếu dữ liệu cho thấy literal translation giảm chất
   lượng đủ đáng kể.

## Engineering closeout sau Phase 9

Sau khi kiến trúc multilingual được khóa: cập nhật demo, tài liệu vận hành và cân
nhắc Docker. Docker không nằm trong scope hiện tại.
