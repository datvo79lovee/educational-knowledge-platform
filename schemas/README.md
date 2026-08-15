# Machine-readable data contracts

Folder này chứa schema được version cho các output của pipeline.

```text
silver_transcript_v1.schema.json
gold_chunk_v1.schema.json
chunking_evaluation_question_v1.schema.json
embedding_index_manifest_v1.schema.json
lexical_index_manifest_v1.schema.json
cross_encoder_reranking_manifest_v1.schema.json
```

JSON Schema chỉ kiểm tra shape và kiểu dữ liệu. Validator pipeline phải kiểm tra
thêm hash, manifest coverage, segment index, source segment range và các invariant
liên record.
