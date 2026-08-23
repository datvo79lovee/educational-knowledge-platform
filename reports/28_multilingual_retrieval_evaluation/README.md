# Phase 9 M3 — Multilingual retrieval evaluation

## Scope

M3 chỉ đọc frozen M1 Ground Truth và M2 full rankings. Không chạy retrieval,
translator, query expansion, reranking hoặc human relabel.

## Headline metrics

| Metric | EN canonical | VI → literal EN | Δ VI - EN |
| --- | ---: | ---: | ---: |
| MRR | 0.596274510 | 0.634226651 | +0.037952141 |
| Recall@1 | 0.400000000 | 0.550000000 | +0.150000000 |
| Recall@3 | 0.750000000 | 0.700000000 | -0.050000000 |
| Recall@5 | 0.800000000 | 0.750000000 | -0.050000000 |
| Full Evidence@3 | 0.500000000 | 0.550000000 | +0.050000000 |

MRR dùng full ranking 861. Full Evidence@3 giữ canonical contract: Top 3 phải phủ
đủ mọi Ground Truth range của intent, không chỉ chứa một relevant chunk.

## Paired diagnostic

First relevant rank outcomes (`VI rank < / = / > EN rank`):

- Improved: 4
- Unchanged: 10
- Degraded: 6

Mean Top-3 overlap: 0.800000000. Exact ordered Top-3 matches:
6/20. Đây là diagnostic, không phải quality metric.

Exact-string controls `mit60001-q-003` và `mit60001-q-022`: metrics giống nhau
giữa hai branches, validation `passed`.

`mit60001-q-008` giữ trace `Minor wording difference`: EN first relevant rank
2, VI rank 7, delta
+5, outcome `degraded`.

## Boundary

Đây là descriptive baseline, không có post-hoc quality gate. M3 không tự mở
`expanded_en`, RRF hoặc experiment mới; quyết định tiếp theo cần user duyệt.
