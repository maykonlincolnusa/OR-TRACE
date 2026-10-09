"""Reference adapter for local use. No durability or multi-process consistency."""

from threading import RLock


class Conflict(ValueError):
    pass


class MemoryLedger:
    def __init__(self):
        self._entities = {}
        self._accounts = {}
        self._transactions = {}
        self._external = {}
        self._outbox = {}
        self._lock = RLock()

    def add_entity(self, entity):
        with self._lock:
            previous = self._entities.get(entity.id)
            if previous and previous != entity:
                raise Conflict("entity identifier already exists with different data")
            self._entities[entity.id] = entity

    def add_account(self, account):
        with self._lock:
            if account.entity_id not in self._entities:
                raise ValueError("unknown entity")
            previous = self._accounts.get(account.id)
            if previous and previous != account:
                raise Conflict("account identifier already exists with different data")
            self._accounts[account.id] = account

    def has_account(self, account_id):
        with self._lock:
            return account_id in self._accounts

    def ingest(self, transactions, events):
        with self._lock:
            staged = dict(self._transactions)
            external = dict(self._external)
            outbox = dict(self._outbox)
            count = 0
            for tx, event in zip(transactions, events):
                if (
                    tx.source_account_id not in self._accounts
                    or tx.destination_account_id not in self._accounts
                ):
                    raise ValueError("unknown account")
                key = (tx.source_system, tx.external_id)
                old_id = external.get(key)
                previous = staged.get(tx.id)
                if old_id is not None and old_id != tx.id:
                    raise Conflict("external identifier belongs to another transaction")
                if previous:
                    if previous != tx:
                        raise Conflict("transaction identifier already exists with different data")
                    continue
                staged[tx.id] = tx
                external[key] = tx.id
                outbox[event.event_id] = event
                count += 1
            if len(transactions) != len(events):
                raise ValueError("one event is required per transaction")
            self._transactions, self._external, self._outbox = staged, external, outbox
            return count

    def snapshot(self):
        with self._lock:
            return tuple(sorted(self._transactions.values(), key=lambda t: (t.occurred_at, t.id)))

    def pending_events(self, limit=100):
        with self._lock:
            return tuple(self._outbox.values())[:limit]

    def mark_published(self, event_id):
        with self._lock:
            self._outbox.pop(event_id, None)
