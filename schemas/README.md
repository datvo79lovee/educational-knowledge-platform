# Machine-readable data contracts

Folder này chứa schema được version cho các output của pipeline.

```text
silver_transcript_v1.schema.json
```

JSON Schema chỉ kiểm tra shape và kiểu dữ liệu. Validator pipeline phải kiểm tra
thêm hash, manifest coverage, segment index và các invariant liên record.
