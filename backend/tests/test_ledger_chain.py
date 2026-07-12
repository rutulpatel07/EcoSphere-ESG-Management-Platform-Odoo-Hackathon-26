"""Unit tests for the ESG ledger hash chain.

Exercises the requirement directly: build a chain of 3 entries, confirm it
verifies, then tamper with one entry and confirm verification pinpoints the
break. Uses the real hashing/verify logic (``app.services.ledger``) over
lightweight in-memory rows, so it needs no database and no third-party test
dependency — run with ``python -m unittest`` or ``pytest``.
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from typing import Any

from app.services.ledger import compute_row_hash, verify_chain


def build_chain(payloads: list[dict[str, Any]]) -> list[SimpleNamespace]:
    """Link payloads into ledger-row-like objects, exactly as append_entry would."""
    rows: list[SimpleNamespace] = []
    prev_hash: str | None = None
    for i, payload in enumerate(payloads, start=1):
        row_hash = compute_row_hash(prev_hash, payload)
        rows.append(
            SimpleNamespace(seq=i, prev_hash=prev_hash, row_hash=row_hash, payload=payload)
        )
        prev_hash = row_hash
    return rows


class LedgerHashChainTest(unittest.TestCase):
    def setUp(self) -> None:
        # 3 inserts.
        self.payloads: list[dict[str, Any]] = [
            {"entry_type": "CARBON", "ref_id": 1, "co2e_kg": "100.000000"},
            {"entry_type": "CARBON", "ref_id": 2, "co2e_kg": "250.500000"},
            {"entry_type": "POINTS", "ref_id": 3, "points": 150},
        ]
        self.rows = build_chain(self.payloads)

    def test_intact_chain_verifies(self) -> None:
        result = verify_chain(self.rows)
        self.assertTrue(result.valid)
        self.assertEqual(result.entries, 3)
        self.assertIsNone(result.broken_at_seq)

    def test_tampered_payload_is_detected(self) -> None:
        # 1 manual tamper: rewrite the middle entry's payload without re-hashing.
        self.rows[1].payload = {**self.payloads[1], "co2e_kg": "999999.000000"}
        result = verify_chain(self.rows)
        self.assertFalse(result.valid)
        self.assertEqual(result.broken_at_seq, 2)

    def test_tampered_row_hash_is_detected(self) -> None:
        # A forged row_hash also fails the recompute at that seq.
        self.rows[1].row_hash = "0" * 64
        result = verify_chain(self.rows)
        self.assertFalse(result.valid)
        self.assertEqual(result.broken_at_seq, 2)

    def test_genesis_prev_hash_is_empty_string_basis(self) -> None:
        # The genesis row hashes against "" (None prev), and a non-None genesis
        # prev_hash must break the chain at seq 1.
        self.rows[0].prev_hash = "deadbeef"
        result = verify_chain(self.rows)
        self.assertFalse(result.valid)
        self.assertEqual(result.broken_at_seq, 1)


if __name__ == "__main__":
    unittest.main()
