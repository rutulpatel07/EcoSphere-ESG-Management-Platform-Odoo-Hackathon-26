"""Legal challenge_lifecycle transitions.

Draft -> Active -> UnderReview -> Completed, and Archived reachable from any
non-terminal state. Archived itself is terminal (no transitions out,
including re-archiving). Anything not listed here is an illegal transition.
"""

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "Draft": {"Active", "Archived"},
    "Active": {"UnderReview", "Archived"},
    "UnderReview": {"Completed", "Archived"},
    "Completed": {"Archived"},
    "Archived": set(),
}


def is_legal_transition(current: str, target: str) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, set())
