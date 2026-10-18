"""Reproducible snapshot identifiers, not signatures or immutable storage."""

import hashlib
import json
from dataclasses import asdict
from datetime import timezone


def snapshot_fingerprint(transactions):
    records = []
    for transaction in sorted(transactions, key=lambda tx: tx.id):
        record = asdict(transaction)
        record["amount"] = format(transaction.amount, "f")
        record["occurred_at"] = transaction.occurred_at.astimezone(timezone.utc).isoformat()
        records.append(record)
    canonical = json.dumps(records, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode()).hexdigest()
