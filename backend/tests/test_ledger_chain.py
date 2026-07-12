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


def build_chain(entries: list[dict[str, Any]]) -> list[SimpleNamespace]:
    """Link entries into ledger-row-like objects, exactly as append_entry would.

    Each entry is a dict with the row's provenance columns (entry_type, ref_table,
    ref_id, actor_user_id) plus its ``payload`` — all of which are folded into the
    row hash.
    """
    rows: list[SimpleNamespace] = []
    prev_hash: str | None = None
    for i, entry in enumerate(entries, start=1):
        row_hash = compute_row_hash(
            prev_hash,
            entry["payload"],
            entry_type=entry["entry_type"],
            ref_table=entry.get("ref_table"),
            ref_id=entry.get("ref_id"),
            actor_user_id=entry.get("actor_user_id"),
        )
        rows.append(
            SimpleNamespace(
                seq=i,
                prev_hash=prev_hash,
                row_hash=row_hash,
                entry_type=entry["entry_type"],
                ref_table=entry.get("ref_table"),
                ref_id=entry.get("ref_id"),
                actor_user_id=entry.get("actor_user_id"),
                payload=entry["payload"],
            )
        )
        prev_hash = row_hash
    return rows


class LedgerHashChainTest(unittest.TestCase):
    def setUp(self) -> None:
        # 3 inserts.
        self.entries: list[dict[str, Any]] = [
            {
                "entry_type": "CARBON",
                "ref_table": "carbon_transactions",
                "ref_id": 1,
                "actor_user_id": 1,
                "payload": {"co2e_kg": "100.000000"},
            },
            {
                "entry_type": "CARBON",
                "ref_table": "carbon_transactions",
                "ref_id": 2,
                "actor_user_id": 1,
                "payload": {"co2e_kg": "250.500000"},
            },
            {
                "entry_type": "POINTS",
                "ref_table": "point_transactions",
                "ref_id": 3,
                "actor_user_id": None,
                "payload": {"points": 150},
            },
        ]
        self.rows = build_chain(self.entries)

    def test_intact_chain_verifies(self) -> None:
        result = verify_chain(self.rows)
        self.assertTrue(result.valid)
        self.assertEqual(result.entries, 3)
        self.assertIsNone(result.broken_at_seq)

    def test_tampered_payload_is_detected(self) -> None:
        # 1 manual tamper: rewrite the middle entry's payload without re-hashing.
        self.rows[1].payload = {**self.entries[1]["payload"], "co2e_kg": "999999.000000"}
        result = verify_chain(self.rows)
        self.assertFalse(result.valid)
        self.assertEqual(result.broken_at_seq, 2)

    def test_tampered_metadata_is_detected(self) -> None:
        # Rewriting a provenance column (not the payload) also breaks the chain,
        # since entry_type/ref_table/ref_id/actor_user_id are folded into the hash.
        self.rows[1].actor_user_id = 999
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
