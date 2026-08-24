"""Grounded answer generation trên Dense Top 3 evidence."""

from src.grounded_answer.contracts import (
    GroundedAnswerRequest,
    GroundedAnswerResponse,
)

# ``service`` is deliberately not re-exported here. It depends on
# ``src.multilingual.translation``, which imports back into this package, so an eager
# re-export makes the cycle fire whenever the translation module is imported first.
# Consumers import ``src.grounded_answer.service`` directly.
__all__ = [
    "GroundedAnswerRequest",
    "GroundedAnswerResponse",
]
