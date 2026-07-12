"""Service layer for the operations / carbon / ledger owner zone.

Business logic lives here so routers stay thin: ``ledger`` owns the append-only
hash chain, ``emissions`` orchestrates operational-record -> carbon-transaction
-> ledger writes atomically, and ``events`` is the in-process pub/sub bus behind
the SSE stream.
"""
