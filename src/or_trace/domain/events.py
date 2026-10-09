from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict


@dataclass(frozen=True)
class Event:
    event_id: str
    event_type: str
    schema_version: int
    occurred_at: datetime
    aggregate_id: str
    correlation_id: str
    payload: Dict[str, Any]
