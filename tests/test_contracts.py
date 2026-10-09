import json
from pathlib import Path

from or_trace.api.app import create_app


def test_versioned_openapi_matches_runtime():
    root = Path(__file__).resolve().parents[1]
    documented = json.loads((root / "docs/openapi.json").read_text())
    assert documented == create_app().openapi()
    amount = documented["components"]["schemas"]["TransactionInput"]["properties"]["amount"]
    assert amount["type"] == "string"
