"""Unit checks cho contract và startup validation không cần load encoder."""

import json
from pathlib import Path

import numpy as np
import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from src.search_api.contracts import SearchRequest, SearchResponse
from src.search_api.service import DenseSearchService
from scripts.embedding.build_mit_60001_index import validated_canonical_input


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
        "schemas/runtime_index_manifest_v1.schema.json",
    ):
        schema = json.loads((PROJECT_ROOT / relative_path).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)


def test_manifest_contract_rejects_wrong_revision() -> None:
    manifest = json.loads(
        (
            PROJECT_ROOT / "data/indexes/mit_60001/manifest.json"
        ).read_text(encoding="utf-8")
    )
    manifest["model_revision"] = "wrong-revision"
    with pytest.raises(ValueError):
        DenseSearchService._validate_manifest_contract(manifest)


def test_index_builder_validates_gold_from_canonical_config() -> None:
    records, config, canonical_hash = validated_canonical_input()

    assert len(records) == 861
    assert config["chunking_config_id"] == "semantic_cosine_wp240_v1"
    assert canonical_hash == "c03abf002c29b784d191eb393670da27b80fed8e0e18798f113d7ff8b7daf432"


def test_index_content_rejects_non_normalized_vector() -> None:
    manifest = json.loads(
        (
            PROJECT_ROOT / "data/indexes/mit_60001/manifest.json"
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



# --- Bounded local demo: route/static serving and diagnostic-leak guard ---


def test_demo_page_and_static_assets_are_served_without_lifespan() -> None:
    """The demo is static: it must serve before any encoder or Ollama is involved."""

    from fastapi.testclient import TestClient

    from src.search_api.app import app

    client = TestClient(app)

    page = client.get("/")
    assert page.status_code == 200
    assert page.headers["content-type"].startswith("text/html")
    assert 'value="en"' in page.text and 'value="vi"' in page.text

    for asset in ("/static/app.js", "/static/app.css"):
        response = client.get(asset)
        assert response.status_code == 200, asset


def test_demo_client_never_references_runtime_diagnostics() -> None:
    """The page must not surface retrieval or model internals to a demo viewer."""

    from src.search_api.app import STATIC_DIR

    forbidden = ("retrieval_query", "original_query", "raw_model_output", "normalization")
    for name in ("index.html", "app.js", "app.css"):
        source = (STATIC_DIR / name).read_text(encoding="utf-8")
        for field in forbidden:
            assert field not in source, f"{name} references {field}"


def test_demo_page_does_not_change_the_answer_contract() -> None:
    """Adding the demo must leave the /answer request/response schema untouched."""

    from src.search_api.app import app

    schema = app.openapi()
    answer_post = schema["paths"]["/answer"]["post"]
    request_ref = answer_post["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    response_ref = answer_post["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]

    assert request_ref.endswith("/GroundedAnswerRequest")
    assert response_ref.endswith("/GroundedAnswerResponse")
    # The demo page is not part of the API contract and must stay out of the schema.
    assert sorted(schema["paths"]) == ["/answer", "/search", "/videos/{video_id}"]
