# Multilingual Runtime V1 — M5.3

## Trạng thái

`PREREGISTERED — NOT EXECUTED`

M5.3 kiểm tra đúng một candidate: canonicalization fail-closed chỉ cho nhánh tiếng Việt khi model đã chọn `decision="abstain"` nhưng còn trả `answer` và/hoặc `supporting_chunk_ids` hợp lệ thuộc Dense Top 3.

Candidate không đổi prompt, model, translator, Dense retriever, index, Ground Truth hay public API. Raw model payload vẫn được giữ để audit; response ứng dụng chỉ được canonicalize thành:

```json
{
  "decision": "abstain",
  "answer": null,
  "supporting_chunk_ids": []
}
```

## Lý do mở M5.3

- M4 quan sát 8/20 lỗi `generation_contract`; cả tám raw payload đều đã chọn `abstain` nhưng vi phạm shape.
- M5.1 đổi prompt giảm mẫu quan sát xuống 1/20 nhưng vẫn fail gate zero-tolerance và candidate đã bị reject.
- M5.2 đã rollback prompt về đúng M4. M5.3 không sửa prompt lần nữa; nó kiểm tra một boundary normalization hẹp, deterministic và application-owned.

Các số trên là quan sát của các attempt đã frozen, không phải bằng chứng nhân quả và không phải tỉ lệ lỗi kỳ vọng.

## Contract candidate

Rule mới chỉ được áp dụng khi đồng thời thỏa:

1. `answer_language == "vi"`;
2. raw `decision == "abstain"`;
3. raw `answer` là `null` hoặc chuỗi không rỗng;
4. raw `supporting_chunk_ids` là danh sách chuỗi;
5. mọi ID đều thuộc Dense Top 3 của đúng request;
6. payload thực sự cần sửa: answer khác `null` hoặc danh sách ID không rỗng.

Payload literal `answer="null"` với IDs rỗng thuộc rule legacy `abstain_literal_to_null`, không được tính là một lần áp dụng M5.3.

Không được repair payload tiếng Anh, unknown chunk ID, malformed type, empty-string answer hoặc quyết định khác `abstain`.

## Gate đã đăng ký trước

- G1: đủ đúng 20 intent theo thứ tự frozen, mỗi intent một translation/retrieval/generation call, không retry, diagnostics đầy đủ, runtime source không đổi trong lúc chạy.
- G2: tổng runtime failure ở mọi layer bằng 0.
- G3: chỉ `src/grounded_answer/service.py` khác baseline M5.2 và các symbol frozen vẫn khớp.
- G4: rule chạy đúng hai chiều với eligibility đã đăng ký; response canonical, không evidence/citation; raw payload vẫn giữ nguyên.

Chỉ khi G1–G4 đều PASS mới chuyển M6 đánh giá chất lượng end-to-end. PASS M5.3 chỉ là runtime/normalization integrity, không chứng minh câu trả lời VI đúng, grounded, ngang EN hay production-ready.

## Negative scope

- Không query expansion, BM25, RRF, reranker hoặc external evidence.
- Không đổi prompt/model/parameter, translator hoặc Dense.
- Không sửa Gold, index, metadata, benchmark hoặc Ground Truth.
- Không retry, cherry-pick output, human review hoặc quality metric trong M5.3.
- Không gọi model trong bước preparation này.

## Artifact

- `m5_3_preregistration.json`: protocol và hash pin canonical trước execution.
- `m5_3_runtime_outputs.jsonl`: chỉ xuất hiện sau khi live execution được duyệt riêng.
- `m5_3_gate_results.json`: chỉ xuất hiện sau execution.
- `m5_3_execution_manifest.json`: chỉ xuất hiện sau execution.
