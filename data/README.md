# Data layout

```text
data/
├── bronze/   raw payload và checkpoint, không commit
├── silver/   transcript đã làm sạch và còn khả năng truy vết
└── gold/     chunk sẵn sàng cho embedding/retrieval
```

Target corpus MIT 6.0001 không tạo bản sao raw transcript riêng. Phạm vi được điều
khiển bằng `target_manifest.csv`; Bronze vẫn là source of truth chung.

Output Silver và Gold của target corpus dự kiến dùng namespace:

```text
data/silver/mit_60001/
data/gold/mit_60001/
```
