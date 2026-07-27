# Quyết định encoder cho semantic chunking experiment

## Quyết định

Semantic boundary experiment v1 dùng encoder:

```text
repository: sentence-transformers/all-MiniLM-L6-v2
library: sentence-transformers
similarity: cosine similarity của normalized embedding
```

Quyết định được giữ lại sau khi so sánh desk research ngày 2026-07-27. Lý do chính
là tốc độ và chi phí lặp thử local cho sample experiment, không phải tuyên bố model
này có accuracy cao nhất trên MIT 6.0001. `BAAI/bge-base-en-v1.5` là ứng viên 768
chiều/context 512 cần đánh giá lại nếu sample retrieval cho thấy MiniLM không đủ.

Model card mô tả đây là sentence-transformers model tạo vector dense 384 chiều cho
sentence và short paragraph, có intended use gồm semantic search, clustering và
sentence similarity. Corpus MIT 6.0001 hiện có `language_code=en`, nên ngôn ngữ đầu
vào phù hợp với encoder English này. [Model card chính thức](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)

## Giới hạn và cách dùng

Model card nói input dài hơn 256 word pieces sẽ bị truncate mặc định. Vì vậy semantic
chunker không encode toàn chunk vượt giới hạn; nó encode các semantic window nhỏ,
và dùng hard guardrail 240 word pieces cho `chunk_text` cuối cùng.

Builder phải ghi repository, commit revision đã tải, thư viện version, tokenizer
revision và dimension 384 vào run report. Không được dùng floating `main` revision
trong một run đã công bố. Nếu không resolve được revision cụ thể trước khi chạy,
pipeline phải dừng thay vì tạo output không tái lập.

## Không phải quyết định embedding index

Encoder này chỉ được chọn để đo cohesion giữa các text window khi chia chunk. Quyết
định embedding model cho vector index ở Phase 6 vẫn phải được đánh giá riêng; không
được suy ra rằng hai mục đích bắt buộc dùng cùng model.
