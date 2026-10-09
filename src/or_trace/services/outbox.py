from or_trace.domain.ports import EventPublisher, Ledger


def dispatch(ledger: Ledger, publisher: EventPublisher, limit: int = 100) -> int:
    """Crash after publish can redeliver: consumers MUST deduplicate event_id."""
    count = 0
    for event in ledger.pending_events(limit):
        publisher.publish(event)
        ledger.mark_published(event.event_id)
        count += 1
    return count
