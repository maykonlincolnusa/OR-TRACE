"""Run: python examples/investigation.py (after editable install). Synthetic data."""

import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from or_trace.domain.models import Account, Entity, EntityKind, Transaction
from or_trace.infrastructure.memory import MemoryLedger
from or_trace.services.ingestion import IngestionService
from or_trace.services.tracing import TraceService


def main():
    ledger = MemoryLedger()
    for name in "ABCD":
        ledger.add_entity(Entity(name, EntityKind.ORGANIZATION, f"Synthetic {name}"))
        ledger.add_account(Account(name, name, "TEST_BANK"))
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    transactions = [
        Transaction("t1", "A", "B", Decimal("1000"), "BRL", now, "demo", "1"),
        Transaction("t2", "B", "C", Decimal("950"), "BRL", now + timedelta(minutes=5), "demo", "2"),
        Transaction(
            "t3", "C", "A", Decimal("920"), "BRL", now + timedelta(minutes=10), "demo", "3"
        ),
        Transaction("t4", "B", "D", Decimal("50"), "BRL", now + timedelta(minutes=6), "demo", "4"),
    ]
    IngestionService(ledger).ingest(transactions, "demo-investigation")
    result = TraceService(ledger).trace("A", "forward", now, now + timedelta(days=1), "BRL")
    result["paths"] = [asdict(path) for path in result["paths"]]
    print(json.dumps(result, default=str, indent=2))


if __name__ == "__main__":
    main()
