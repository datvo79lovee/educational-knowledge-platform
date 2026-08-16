"""Unit checks cho contract và startup validation không cần load encoder."""

import json
from pathlib import Path

import numpy as np
import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from src.search_api.contracts import SearchRequest, SearchResponse
from src.search_api.service import DenseSearchService


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_search_request_trims_and_rejects_extra_fields() -> None:
    assert SearchRequest(query="  computation  ").query == "computation"
    with pytest.raises(ValidationError):
        SearchRequest(query="   ")
    with pytest.raises(ValidationError):
        SearchRequest(query="computation", top_k=10)


def test_search_response_requires_exactly_three_results() -> None:
    with pytest.raises(ValidationError):
        SearchResponse(
            query="computation",
            retrieval_method="dense_baseline_v1",
            index_run_id="index",
            result_count=3,
            results=[],
        )


def test_static_schemas_are_valid_draft_2020_12() -> None:
    for relative_path in (
        "schemas/search_api_v1.schema.json",
        "schemas/search_api_validation_manifest_v1.schema.json",
    ):
        schema = json.loads((PROJECT_ROOT / relative_path).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)


def test_manifest_contract_rejects_wrong_revision() -> None:
    manifest = json.loads(
        (
            PROJECT_ROOT / "reports/09_embedding/embedding_index_manifest.json"
        ).read_text(encoding="utf-8")
    )
    manifest["model_revision"] = "wrong-revision"
    with pytest.raises(ValueError):
        DenseSearchService._validate_manifest_contract(manifest)


def test_index_content_rejects_non_normalized_vector() -> None:
    manifest = json.loads(
        (
            PROJECT_ROOT / "reports/09_embedding/embedding_index_manifest.json"
        ).read_text(encoding="utf-8")
    )
    chunks = [
        json.loads(line)
        for line in (
            PROJECT_ROOT / "data/gold/mit_60001/chunks.jsonl"
        ).read_text(encoding="utf-8").splitlines()
        if line
    ]
    metadata = [
        json.loads(line)
        for line in (
            PROJECT_ROOT / "data/indexes/mit_60001/metadata.jsonl"
        ).read_text(encoding="utf-8").splitlines()
        if line
    ]
    vectors = np.load(
        PROJECT_ROOT / "data/indexes/mit_60001/embeddings.npy",
        allow_pickle=False,
    )
    invalid = vectors.copy()
    invalid[0] = 0
    with pytest.raises(ValueError):
        DenseSearchService._validate_index_content(manifest, chunks, metadata, invalid)

