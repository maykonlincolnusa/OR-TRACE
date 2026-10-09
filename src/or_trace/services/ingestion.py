from dataclasses import asdict
from datetime import datetime, timezone
from uuid import uuid4

from or_trace.domain.events import Event
from or_trace.domain.ports import Ledger


class IngestionService:
    def __init__(self, ledger: Ledger):
        self.ledger = ledger

    def ingest(self, transactions, correlation_id):
        events = []
        for tx in transactions:
            payload = asdict(tx)
            payload["amount"] = format(tx.amount, "f")
            payload["occurred_at"] = tx.occurred_at.isoformat()
            events.append(
                Event(
                    str(uuid4()),
                    "transaction.ingested",
                    1,
                    datetime.now(timezone.utc),
                    tx.id,
                    correlation_id,
                    payload,
                )
            )
        return self.ledger.ingest(transactions, events)
