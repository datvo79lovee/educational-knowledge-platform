"""Download and verify the exact canonical Dense query encoder revision.

Ollama is intentionally outside this bootstrap step. ``POST /search`` needs only
this encoder and the committed canonical Gold/index artifacts; ``POST /answer``
additionally needs the separately managed local Ollama runtime.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INDEX_MANIFEST_FILE = PROJECT_ROOT / "reports/09_embedding/embedding_index_manifest.json"


def load_manifest() -> dict[str, Any]:
    manifest = json.loads(INDEX_MANIFEST_FILE.read_text(encoding="utf-8"))
    if manifest.get("validation_status") != "passed":
        raise ValueError("Canonical embedding index manifest is not validated")
    return manifest


def model_commit_hash(model: Any) -> str | None:
    return getattr(model._first_module().auto_model.config, "_commit_hash", None)


def validate_model(model: Any, manifest: dict[str, Any]) -> None:
    expected_revision = str(manifest["model_revision"])
    actual_revision = model_commit_hash(model)
    if actual_revision != expected_revision:
        raise RuntimeError(
            "Query encoder revision mismatch: "
            f"expected {expected_revision}, got {actual_revision}"
        )
    if model.get_embedding_dimension() != manifest["embedding_dimension"]:
        raise RuntimeError("Query encoder dimension differs from index manifest")
    if model.max_seq_length != manifest["model_max_sequence_length"]:
        raise RuntimeError("Query encoder max sequence length differs from index manifest")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--hf-home",
        type=Path,
        help="Optional isolated Hugging Face cache root used for clean-room validation.",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Do not use the network; verify that the exact revision is already cached.",
    )
    args = parser.parse_args()

    cache_folder: Path | None = None
    if args.hf_home is not None:
        hf_home = args.hf_home.resolve()
        hf_home.mkdir(parents=True, exist_ok=True)
        cache_folder = hf_home / "hub"
        os.environ["HF_HOME"] = str(hf_home)
        os.environ["HUGGINGFACE_HUB_CACHE"] = str(cache_folder)
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

    # Import only after the optional isolated cache environment has been applied.
    from sentence_transformers import SentenceTransformer

    manifest = load_manifest()
    repository = str(manifest["model_repository"])
    revision = str(manifest["model_revision"])
    model_kwargs: dict[str, Any] = {
        "revision": revision,
        "local_files_only": args.verify_only,
        "device": "cpu",
    }
    if cache_folder is not None:
        model_kwargs["cache_folder"] = str(cache_folder)

    model = SentenceTransformer(repository, **model_kwargs)
    validate_model(model, manifest)

    # A second local-only load proves that the runtime's no-download startup mode works.
    local_kwargs = dict(model_kwargs)
    local_kwargs["local_files_only"] = True
    local_model = SentenceTransformer(repository, **local_kwargs)
    validate_model(local_model, manifest)

    print(
        json.dumps(
            {
                "bootstrap_status": "passed",
                "local_only_reload": "passed",
                "model_repository": repository,
                "model_revision": revision,
                "embedding_dimension": manifest["embedding_dimension"],
                "model_max_sequence_length": manifest["model_max_sequence_length"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
