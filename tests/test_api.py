import pytest
from fastapi.testclient import TestClient

from or_trace.api.app import create_app


def test_auth_and_production_guard():
    client = TestClient(create_app(api_key="secret"))
    assert client.post("/v1/entities", json={}).status_code == 401
    assert client.get("/health/live").status_code == 200
    with pytest.raises(RuntimeError):
        create_app(environment="production", api_key="")
    with pytest.raises(RuntimeError):
        create_app(environment="production", api_key="secret")


def test_ingest_trace_validation_and_audit(ledger):
    records = []

    class Audit:
        def record(self, record):
            records.append(record)

    client = TestClient(create_app(ledger=ledger, audit=Audit(), api_key="secret"))
    headers = {"X-API-Key": "secret"}
    tx = {
        "id": "t1",
        "source_account_id": "A",
        "destination_account_id": "B",
        "amount": "100.00",
        "currency": "BRL",
        "occurred_at": "2026-01-01T01:00:00-03:00",
        "source_system": "core",
        "external_id": "ext1",
    }
    response = client.post("/v1/transactions", headers=headers, json={"transactions": [tx]})
    assert response.json() == {"accepted": 1, "duplicates": 0}
    assert response.headers["x-correlation-id"] == records[-1]["correlation_id"]
    assert (
        client.post("/v1/transactions", headers=headers, json={"transactions": [tx]}).json()[
            "duplicates"
        ]
        == 1
    )
    params = {"start": "2026-01-01T00:00:00Z", "end": "2026-01-02T00:00:00Z", "currency": "BRL"}
    result = client.get("/v1/accounts/A/trace", headers=headers, params=params)
    assert result.status_code == 200
    assert result.json()["paths"][0]["bottleneck_amount"] == "100.00"
    assert ledger.snapshot()[0].occurred_at.isoformat() == "2026-01-01T04:00:00+00:00"
    assert (
        client.get("/v1/accounts/missing/trace", headers=headers, params=params).status_code == 404
    )
    assert (
        client.get(
            "/v1/accounts/A/trace", headers=headers, params={**params, "max_hops": 11}
        ).status_code
        == 422
    )
    for value in (100.1, "NaN", "0"):
        assert (
            client.post(
                "/v1/transactions",
                headers=headers,
                json={"transactions": [{**tx, "amount": value}]},
            ).status_code
            == 422
        )
    assert "or_trace_requests_total" in client.get("/metrics", headers=headers).text
