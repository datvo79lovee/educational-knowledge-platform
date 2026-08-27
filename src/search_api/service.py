"""Runtime Dense retrieval dùng canonical MIT 6.0001 index.

Service kiểm tra toàn bộ hash và invariant trước khi load query encoder. Mọi request
dùng lại cùng model/index đã load; không rebuild index và không tải model từ mạng.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from threading import Lock
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INDEX_MANIFEST_FILE = Path("data/indexes/mit_60001/manifest.json")
RETRIEVAL_DECISION_FILE = Path("docs/decisions/CANONICAL_RUNTIME_DECISIONS.md")
CANONICAL_GOLD_FILE = Path("data/gold/mit_60001/chunks.jsonl")
EMBEDDINGS_FILE = Path("data/indexes/mit_60001/embeddings.npy")
METADATA_FILE = Path("data/indexes/mit_60001/metadata.jsonl")

RETRIEVAL_METHOD = "dense_baseline_v1"
INDEX_BACKEND = "numpy_exact_cosine_v1"
SCOPE_VERSION = "mit_60001_fall_2016_v1"
CHUNKING_CONFIG_ID = "semantic_cosine_wp240_v1"
MODEL_REPOSITORY = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
EMBEDDING_DIMENSION = 384
TOP_K = 3


def _sha256_file(path: Path) -> str:
    """Tính SHA-256 theo stream để không đọc cả artifact lớn vào RAM."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Đọc JSONL và bỏ qua dòng trống."""

    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}") from exc
    return records


def _required_file(project_root: Path, relative_path: Path) -> Path:
    """Resolve artifact trong project và dừng sớm nếu file bị thiếu."""

    path = project_root / relative_path
    if not path.is_file():
        raise FileNotFoundError(f"Required Search API artifact is missing: {relative_path}")
    return path


class DenseSearchService:
    """Read-only exact cosine retrieval trên 861 canonical chunks."""

    def __init__(
        self,
        *,
        manifest: dict[str, Any],
        chunks: list[dict[str, Any]],
        metadata: list[dict[str, Any]],
        vectors: np.ndarray,
        model: SentenceTransformer,
    ) -> None:
        self._manifest = manifest
        self._chunks = chunks
        self._metadata = metadata
        self._vectors = vectors
        self._model = model
        # SentenceTransformer/PyTorch inference dùng chung model; lock giữ request
        # đồng thời không làm thay đổi tính ổn định của thứ hạng MVP.
        self._encode_lock = Lock()
        self._videos = self._build_video_catalog()

    @property
    def index_run_id(self) -> str:
        """ID của canonical index đang phục vụ."""

        return str(self._manifest["index_run_id"])

    @classmethod
    def load(cls, project_root: Path = PROJECT_ROOT) -> "DenseSearchService":
        """Validate source of truth rồi load model/index đúng một lần khi startup."""

        manifest_path = _required_file(project_root, INDEX_MANIFEST_FILE)
        decision_path = _required_file(project_root, RETRIEVAL_DECISION_FILE)
        gold_path = _required_file(project_root, CANONICAL_GOLD_FILE)
        embeddings_path = _required_file(project_root, EMBEDDINGS_FILE)
        metadata_path = _required_file(project_root, METADATA_FILE)

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        cls._validate_manifest_contract(manifest)
        cls._validate_retrieval_decision(decision_path)

        expected_hashes = {
            gold_path: manifest["canonical_gold_sha256"],
            embeddings_path: manifest["embeddings_sha256"],
            metadata_path: manifest["metadata_sha256"],
        }
        for path, expected_hash in expected_hashes.items():
            actual_hash = _sha256_file(path)
            if actual_hash != expected_hash:
                raise ValueError(
                    f"Artifact hash mismatch for {path.relative_to(project_root)}: "
                    f"expected {expected_hash}, got {actual_hash}"
                )

        chunks = _load_jsonl(gold_path)
        metadata = _load_jsonl(metadata_path)
        vectors = np.load(embeddings_path, allow_pickle=False)
        cls._validate_index_content(manifest, chunks, metadata, vectors)
        model = cls._load_model(manifest)
        return cls(
            manifest=manifest,
            chunks=chunks,
            metadata=metadata,
            vectors=vectors,
            model=model,
        )

    @staticmethod
    def _validate_manifest_contract(manifest: dict[str, Any]) -> None:
        """Khóa runtime vào đúng Phase 6 index contract đã được chọn."""

        expected = {
            "schema_version": "runtime_index_manifest_v1",
            "validation_status": "passed",
            "scope_version": SCOPE_VERSION,
            "selected_chunking_config_id": CHUNKING_CONFIG_ID,
            "index_backend": INDEX_BACKEND,
            "canonical_gold_file": str(CANONICAL_GOLD_FILE).replace("\\", "/"),
            "model_repository": MODEL_REPOSITORY,
            "model_revision": MODEL_REVISION,
            "embedding_dimension": EMBEDDING_DIMENSION,
            "embedding_dtype": "float32",
            "normalize_embeddings": True,
            "embeddings_file": str(EMBEDDINGS_FILE).replace("\\", "/"),
            "metadata_file": str(METADATA_FILE).replace("\\", "/"),
        }
        mismatches = {
            field: (expected_value, manifest.get(field))
            for field, expected_value in expected.items()
            if manifest.get(field) != expected_value
        }
        if mismatches:
            raise ValueError(f"Embedding index manifest differs from API contract: {mismatches}")

    @staticmethod
    def _validate_retrieval_decision(path: Path) -> None:
        """Không cho API chạy nếu decision artifact không chọn Dense baseline."""

        decision_text = path.read_text(encoding="utf-8")
        if "`dense_baseline_v1` is the canonical retriever" not in decision_text:
            raise ValueError("Retrieval decision does not select dense_baseline_v1")

    @staticmethod
    def _validate_index_content(
        manifest: dict[str, Any],
        chunks: list[dict[str, Any]],
        metadata: list[dict[str, Any]],
        vectors: np.ndarray,
    ) -> None:
        """Kiểm tra shape, vector và mapping vị trí trước khi nhận request."""

        expected_shape = tuple(manifest["embedding_shape"])
        if vectors.shape != expected_shape or vectors.dtype != np.float32:
            raise ValueError(
                f"Unexpected embedding array: shape={vectors.shape}, dtype={vectors.dtype}"
            )
        if len(chunks) != manifest["chunk_count"] or len(metadata) != len(chunks):
            raise ValueError("Gold, metadata and manifest record counts differ")
        if not np.isfinite(vectors).all():
            raise ValueError("Embedding index contains NaN or Infinity")
        norm_tolerance = float(manifest["norm_tolerance"])
        if np.any(np.abs(np.linalg.norm(vectors, axis=1) - 1.0) > norm_tolerance):
            raise ValueError("Embedding index contains a non-normalized vector")

        seen_chunk_ids: set[str] = set()
        for position, (chunk, item) in enumerate(zip(chunks, metadata, strict=True)):
            chunk_id = chunk.get("chunk_id")
            if not chunk_id or chunk_id in seen_chunk_ids:
                raise ValueError(f"Missing or duplicate chunk_id at position {position}")
            seen_chunk_ids.add(chunk_id)
            if item.get("index_position") != position or item.get("chunk_id") != chunk_id:
                raise ValueError(f"Metadata order differs from Gold at position {position}")
            if item.get("video_id") != chunk.get("video_id"):
                raise ValueError(f"Video mapping differs at position {position}")
            if item.get("start_second") != chunk.get("start_second") or item.get(
                "end_second"
            ) != chunk.get("end_second"):
                raise ValueError(f"Citation timing differs at position {position}")
            if not str(chunk.get("chunk_text", "")).strip():
                raise ValueError(f"Empty chunk text at position {position}")
            if not str(item.get("source_url", "")).startswith(
                "https://www.youtube.com/watch?v="
            ):
                raise ValueError(f"Invalid source URL at position {position}")

        if len({chunk["video_id"] for chunk in chunks}) != manifest["video_count"]:
            raise ValueError("Gold video count differs from index manifest")

    @staticmethod
    def _load_model(manifest: dict[str, Any]) -> SentenceTransformer:
        """Load pinned encoder từ cache local; tuyệt đối không download khi startup."""

        model = SentenceTransformer(
            MODEL_REPOSITORY,
            revision=MODEL_REVISION,
            local_files_only=True,
            device="cpu",
        )
        actual_revision = getattr(model._first_module().auto_model.config, "_commit_hash", None)
        if actual_revision != MODEL_REVISION:
            raise RuntimeError(
                f"Loaded query encoder revision mismatch: expected {MODEL_REVISION}, "
                f"got {actual_revision}"
            )
        if model.get_embedding_dimension() != manifest["embedding_dimension"]:
            raise RuntimeError("Query encoder dimension differs from index manifest")
        if model.max_seq_length != manifest["model_max_sequence_length"]:
            raise RuntimeError("Query encoder max sequence length differs from index manifest")
        return model

    def _build_video_catalog(self) -> dict[str, dict[str, Any]]:
        """Tổng hợp endpoint video từ canonical metadata, không truy vấn PostgreSQL."""

        grouped: dict[str, list[dict[str, Any]]] = {}
        for item in self._metadata:
            grouped.setdefault(str(item["video_id"]), []).append(item)

        catalog: dict[str, dict[str, Any]] = {}
        for video_id, items in grouped.items():
            titles = {str(item["video_title"]) for item in items}
            source_urls = {str(item["source_url"]) for item in items}
            if len(titles) != 1 or len(source_urls) != 1:
                raise ValueError(f"Conflicting metadata for video {video_id}")
            catalog[video_id] = {
                "video_id": video_id,
                "video_title": titles.pop(),
                "source_url": source_urls.pop(),
                "chunk_count": len(items),
                "start_second": min(float(item["start_second"]) for item in items),
                "end_second": max(float(item["end_second"]) for item in items),
            }
        return catalog

    def search(self, query: str) -> list[dict[str, Any]]:
        """Encode một query và trả đúng Dense Top 3 theo tie-break đã khóa."""

        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("query must not be empty or whitespace-only")

        with self._encode_lock:
            query_vector = self._model.encode(
                [normalized_query],
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
        query_vector = np.asarray(query_vector, dtype=np.float32, order="C")
        if query_vector.shape != (1, EMBEDDING_DIMENSION) or not np.isfinite(
            query_vector
        ).all():
            raise RuntimeError("Query encoder returned an invalid vector")

        scores = query_vector[0] @ self._vectors.T
        ranked_indices = sorted(
            range(len(self._chunks)),
            key=lambda index: (-float(scores[index]), self._chunks[index]["chunk_id"]),
        )[:TOP_K]

        results: list[dict[str, Any]] = []
        for rank, index in enumerate(ranked_indices, start=1):
            chunk = self._chunks[index]
            item = self._metadata[index]
            source_url = str(item["source_url"])
            start_second = float(item["start_second"])
            results.append(
                {
                    "rank": rank,
                    "chunk_id": str(chunk["chunk_id"]),
                    "chunk_text": str(chunk["chunk_text"]),
                    "score": float(scores[index]),
                    "video_id": str(item["video_id"]),
                    "video_title": str(item["video_title"]),
                    "start_second": start_second,
                    "end_second": float(item["end_second"]),
                    "source_url": source_url,
                    "citation_url": f"{source_url}&t={math.floor(start_second)}s",
                }
            )
        return results

    def get_video(self, video_id: str) -> dict[str, Any] | None:
        """Trả metadata target video hoặc ``None`` nếu ID nằm ngoài corpus."""

        return self._videos.get(video_id)
