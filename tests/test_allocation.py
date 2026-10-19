from conftest import ingest, transaction
from test_tracing import trace


def test_overlapping_paths_do_not_allocate_shared_transfer_twice(ledger):
    ingest(ledger, transaction("t1", "A", "B", amount="100"),
           transaction("t2", "B", "C", minute=1, amount="60"),
           transaction("t3", "B", "D", minute=2, amount="60"))
    result = trace(ledger)
    assert result["allocated_total"] == "100"
    assert [item["amount"] for item in result["conservative_allocations"]] == ["60", "40"]
