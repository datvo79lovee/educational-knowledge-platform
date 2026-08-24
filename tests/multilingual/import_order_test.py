"""Guard the runtime package against the circular import between the VI branch modules.

``src.multilingual.translation`` imports the Ollama provider from
``src.grounded_answer``, and ``src.grounded_answer.service`` imports back into
``src.multilingual.translation``. Whether that cycle fires depends on which module is
imported first, so the check only means something in a fresh interpreter: inside a
pytest process the import graph is already warm and a plain ``import`` would pass even
while the cycle exists.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]

IMPORT_ORDERS = [
    pytest.param("import src.multilingual.translation", id="translation_first"),
    pytest.param("import src.grounded_answer.service", id="grounded_answer_first"),
    pytest.param(
        "import src.multilingual.translation, src.grounded_answer.service",
        id="translation_then_grounded_answer",
    ),
    pytest.param(
        "import src.grounded_answer.service, src.multilingual.translation",
        id="grounded_answer_then_translation",
    ),
]


@pytest.mark.parametrize("statement", IMPORT_ORDERS)
def test_runtime_modules_import_in_any_order(statement: str) -> None:
    """Every import order must succeed in a fresh interpreter."""

    completed = subprocess.run(
        [sys.executable, "-c", statement],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, (
        f"Import order failed: {statement}\n{completed.stderr.strip()}"
    )
