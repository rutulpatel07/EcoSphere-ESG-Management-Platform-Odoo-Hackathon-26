"""Legal state-machine transitions for lifecycle-style status fields.

Generic ``is_legal_transition(transitions, current, target)`` plus one
transition map per state machine in this owner zone.
"""

CHALLENGE_TRANSITIONS: dict[str, set[str]] = {
    "Draft": {"Active", "Archived"},
    "Active": {"UnderReview", "Archived"},
    "UnderReview": {"Completed", "Archived"},
    "Completed": {"Archived"},
    "Archived": set(),
}
"""Draft -> Active -> UnderReview -> Completed, Archived reachable from any
non-terminal state; Archived itself is terminal (no re-archiving)."""

COMPLIANCE_ISSUE_TRANSITIONS: dict[str, set[str]] = {
    "OPEN": {"IN_PROGRESS", "RESOLVED"},
    "IN_PROGRESS": {"RESOLVED", "OPEN"},
    "RESOLVED": {"CLOSED", "IN_PROGRESS"},
    "CLOSED": set(),
}
"""OPEN -> IN_PROGRESS -> RESOLVED -> CLOSED, with RESOLVED/IN_PROGRESS
reopenable into each other; CLOSED is terminal."""


def is_legal_transition(transitions: dict[str, set[str]], current: str, target: str) -> bool:
    return target in transitions.get(current, set())
