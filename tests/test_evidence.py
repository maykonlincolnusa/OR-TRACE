from datetime import datetime

import pytest
from conftest import ingest, transaction
from test_tracing import END, START, trace

from or_trace.services.evidence import snapshot_fingerprint
from or_trace.services.tracing import TraceService


@pytest.mark.parametrize("name,value", [
    ("max_hops", 0), ("max_paths", -1), ("max_expansions", True),
    ("max_hops", 11), ("max_paths", 1001), ("max_expansions", 10001),
])
def test_service_rejects_invalid_budgets(ledger, name, value):
    with pytest.raises(ValueError):
        trace(ledger, **{name: value})


def test_service_rejects_naive_bounds_and_invalid_currency(ledger):
    service = TraceService(ledger)
    with pytest.raises(ValueError):
        service.trace("A", "forward", datetime(2026, 1, 1), END, "BRL")
    with pytest.raises(ValueError):
        service.trace("A", "forward", START, END, "brl")


def test_snapshot_hash_is_order_independent_and_sensitive_to_records():
    a, b = transaction("a", "A", "B"), transaction("b", "B", "C", 1)
    assert snapshot_fingerprint([a, b]) == snapshot_fingerprint([b, a])
    assert snapshot_fingerprint([a]) != snapshot_fingerprint([a, b])


def test_response_fingerprint_covers_only_query_dataset(ledger):
    a = transaction("a", "A", "B")
    ingest(ledger, a, transaction("usd", "B", "C", 1, currency="USD"))
    result = trace(ledger)
    assert result["snapshot_sha256"] == snapshot_fingerprint([a])
    assert result["transaction_count"] == 1
