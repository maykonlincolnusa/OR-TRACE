from datetime import datetime, timezone

from conftest import ingest, transaction

from or_trace.services.tracing import TraceService

START = datetime(2026, 1, 1, tzinfo=timezone.utc)
END = datetime(2026, 1, 2, tzinfo=timezone.utc)


def trace(ledger, account="A", direction="forward", **kwargs):
    return TraceService(ledger).trace(account, direction, START, END, "BRL", **kwargs)


def test_lineage_both_directions_and_explanation(ledger):
    ingest(ledger, transaction("1", "A", "B"), transaction("2", "B", "C", 10, "95"))
    forward = trace(ledger)["paths"][0]
    backward = trace(ledger, "C", "backward")["paths"][0]
    assert forward == backward
    assert forward.transaction_ids == ("1", "2")
    assert str(forward.bottleneck_amount) == "95"
    assert forward.risk_score == 45
    assert {f.code for f in forward.findings} == {"rapid_movement", "pass_through"}


def test_time_currency_and_equal_timestamp_do_not_create_false_path(ledger):
    ingest(
        ledger,
        transaction("1", "A", "B", 10),
        transaction("2", "B", "C", 5),
        transaction("3", "B", "D", 20, currency="USD"),
        transaction("4", "B", "E", 10),
    )
    assert trace(ledger)["paths"][0].transaction_ids == ("1",)


def test_cycle_stops_and_is_explained(ledger):
    ingest(
        ledger,
        transaction("1", "A", "B"),
        transaction("2", "B", "C", 1),
        transaction("3", "C", "A", 2),
    )
    path = trace(ledger)["paths"][0]
    assert path.terminated_by_cycle
    assert "circular_flow" in {f.code for f in path.findings}
    assert path.risk_score == 75


def test_fan_in_and_out(ledger):
    ingest(
        ledger,
        transaction("1", "A", "B"),
        transaction("2", "A", "C", 1),
        transaction("3", "A", "D", 2),
        transaction("4", "E", "B", 1),
        transaction("5", "F", "B", 2),
    )
    codes = {f.code for p in trace(ledger)["paths"] for f in p.findings}
    assert codes == {"fan_in", "fan_out"}


def test_limits_are_reported(ledger):
    ingest(ledger, transaction("1", "A", "B"), transaction("2", "B", "C", 1))
    result = trace(ledger, max_hops=1)
    assert result["truncated"]
    assert len(result["paths"][0].transaction_ids) == 1
    assert trace(ledger, max_expansions=1)["truncated"]


def test_window_excludes_transactions(ledger):
    ingest(ledger, transaction("1", "A", "B", -1))
    assert trace(ledger)["paths"] == []
