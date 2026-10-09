from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from or_trace.domain.models import Account, Entity, EntityKind, Transaction
from or_trace.infrastructure.memory import MemoryLedger
from or_trace.services.ingestion import IngestionService


@pytest.fixture
def ledger():
    store = MemoryLedger()
    for name in "ABCDEFG":
        store.add_entity(Entity(name, EntityKind.PERSON, name))
        store.add_account(Account(name, name, "TEST"))
    return store


def transaction(identifier, source, destination, minute=0, amount="100", currency="BRL"):
    return Transaction(
        identifier,
        source,
        destination,
        Decimal(amount),
        currency,
        datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=minute),
        "test",
        identifier,
    )


def ingest(ledger, *transactions):
    return IngestionService(ledger).ingest(transactions, "test-correlation")
