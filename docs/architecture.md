# Engineering decisions

## ADR 001 — Independent domain

Dataclasses and `Decimal` define immutable financial facts. Protocols define ports; FastAPI, Pydantic, and storage stay at the boundaries. Services receive the Ledger through dependency injection. Currency currently uses a three-letter code and supports up to eight decimal places. ISO 4217 membership and currency-specific scale are future validations.

## ADR 002 — Atomic ledger and outbox

Transactions and events must be persisted in one unit of work so committed facts cannot lose notifications. The memory adapter uses a lock and copy-before-commit. A PostgreSQL adapter should use transactions and unique constraints while comparing retry content; `ON CONFLICT DO NOTHING` alone could hide divergent payloads.

Internal ID and `(source_system, external_id)` are unique. Identical reprocessing is a no-op. The dispatcher provides at-least-once delivery: consumers need an inbox or event key updated atomically with their local projection, retry/backoff, dead-letter handling, and replay procedures.

## ADR 003 — Graph as a rebuildable projection

Entity and Account are nodes; OWNS links an entity to an account; TRANSFER links accounts and carries transaction ID, amount, currency, and time. `transaction.ingested` consumers perform idempotent upserts. The current query engine reads a consistent Ledger snapshot; the `GraphProjection` port describes a future projection.

Production designs must expose projection lag and a consistent watermark. Registration-change events and a durable graph adapter are not implemented.

## ADR 004 — No false ownership inference

The traversal enumerates temporally valid paths in one currency with strictly increasing timestamps. Backward search reverses navigation but returns chronological lineage. Equal timestamps do not establish causality. Traversal stops on the first repeated account.

The minimum edge amount is only a per-path upper bound. The engine does not allocate conserved funds across overlapping paths, apply FIFO/LIFO/proportional taint, convert FX, reconstruct prior balances, or infer economic origin and beneficial ownership. Any stronger attribution needs an explicit policy, balance reconciliation, and validation.

## ADR 005 — Query budgets and evidence snapshots

Queries accept 1–10 hops and 1–1,000 paths, with an internal expansion budget. Inputs require time-zone-aware dates, a valid currency code, and bounded windows. Every result records the number of transactions in the analyzed snapshot and a SHA-256 fingerprint of its canonical representation. This supports reproducibility but is not a signature or proof that upstream data was complete.

Path enumeration can grow exponentially. Production work includes indexed window queries, asynchronous jobs, tenant quotas, cancellation, timeouts, memory budgets, pagination, and visible truncation.

## ADR 006 — Explainable risk

The versioned heuristic score sums distinct rule weights and caps at 100. It is not a probability, regulatory classification, or automatic decision. Evidence names the transactions and accounts supporting each hypothesis. Rule changes require a new version, governance approval, and regression and detection-quality testing.
