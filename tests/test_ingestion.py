from dataclasses import replace
from decimal import Decimal

import pytest
from conftest import ingest, transaction

from or_trace.infrastructure.memory import Conflict
from or_trace.services.outbox import dispatch


def test_idempotency_and_atomic_outbox(ledger):
    tx = transaction("1", "A", "B")
    assert ingest(ledger, tx) == 1
    assert ingest(ledger, tx) == 0
    assert len(ledger.snapshot()) == len(ledger.pending_events()) == 1
    event = ledger.pending_events()[0]
    assert event.payload["amount"] == "100"
    assert event.correlation_id == "test-correlation"


def test_batch_rolls_back_on_conflict(ledger):
    tx = transaction("1", "A", "B")
    ingest(ledger, tx)
    with pytest.raises(Conflict):
        ingest(ledger, transaction("2", "B", "C"), replace(tx, amount=Decimal("200")))
    assert len(ledger.snapshot()) == len(ledger.pending_events()) == 1


def test_external_key_collision_and_missing_account(ledger):
    tx = transaction("1", "A", "B")
    ingest(ledger, tx)
    with pytest.raises(Conflict):
        ingest(ledger, replace(tx, id="2"))
    with pytest.raises(ValueError):
        ingest(ledger, transaction("3", "A", "unknown"))


def test_invalid_amounts():
    for value in ("0", "-1", "NaN", "Infinity"):
        with pytest.raises(ValueError):
            transaction("1", "A", "B", amount=value)


def test_publisher_failure_keeps_pending_event(ledger):
    ingest(ledger, transaction("1", "A", "B"))

    class Failure:
        def publish(self, event):
            raise RuntimeError("broker unavailable")

    with pytest.raises(RuntimeError):
        dispatch(ledger, Failure())
    assert len(ledger.pending_events()) == 1

    class Success:
        def publish(self, event):
            pass

    assert dispatch(ledger, Success()) == 1
    assert ledger.pending_events() == ()
