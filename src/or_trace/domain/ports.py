"""Ports for SQL source of truth, graph projection and broker adapters."""

from typing import Protocol, Sequence

from .events import Event
from .models import Account, Entity, Transaction


class Ledger(Protocol):
    def add_entity(self, entity: Entity) -> None: ...
    def add_account(self, account: Account) -> None: ...
    def ingest(self, transactions: Sequence[Transaction], events: Sequence[Event]) -> int:
        """Atomically persist batch and outbox; identical retries are no-ops."""
        ...

    def snapshot(self) -> Sequence[Transaction]: ...
    def has_account(self, account_id: str) -> bool: ...
    def pending_events(self, limit: int) -> Sequence[Event]: ...
    def mark_published(self, event_id: str) -> None: ...


class EventPublisher(Protocol):
    def publish(self, event: Event) -> None:
        """Return only after durable broker confirmation; delivery is at least once."""
        ...


class GraphProjection(Protocol):
    def apply(self, event: Event) -> None:
        """Idempotently apply event using event_id deduplication."""
        ...

    def adjacent(self, account_id: str, direction: str) -> Sequence[Transaction]: ...


class AuditSink(Protocol):
    def record(self, record: dict) -> None: ...
