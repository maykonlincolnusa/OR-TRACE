-- Reference design, not a shipped adapter or migration runner.
-- Source of truth: transactions and outbox MUST share the same DB transaction.
CREATE TABLE entities (
    id text PRIMARY KEY,
    kind text NOT NULL CHECK (kind IN ('person', 'organization')),
    display_name text NOT NULL
);
CREATE TABLE accounts (
    id text PRIMARY KEY,
    entity_id text NOT NULL REFERENCES entities(id),
    institution text NOT NULL
);
CREATE TABLE transactions (
    id text PRIMARY KEY,
    source_account_id text NOT NULL REFERENCES accounts(id),
    destination_account_id text NOT NULL REFERENCES accounts(id),
    amount numeric(28,8) NOT NULL CHECK (amount > 0 AND amount < 'Infinity'::numeric),
    currency char(3) NOT NULL CHECK (currency ~ '^[A-Z]{3}$'),
    occurred_at timestamptz NOT NULL,
    source_system text NOT NULL,
    external_id text NOT NULL,
    UNIQUE (source_system, external_id),
    CHECK (source_account_id <> destination_account_id)
);
CREATE INDEX transactions_source_time ON transactions(source_account_id, currency, occurred_at);
CREATE INDEX transactions_destination_time ON transactions(destination_account_id, currency, occurred_at);
CREATE TABLE outbox (
    event_id uuid PRIMARY KEY,
    aggregate_id text NOT NULL,
    event_type text NOT NULL,
    schema_version integer NOT NULL,
    occurred_at timestamptz NOT NULL,
    correlation_id text NOT NULL,
    payload jsonb NOT NULL,
    published_at timestamptz,
    attempts integer NOT NULL DEFAULT 0
);
CREATE INDEX outbox_pending ON outbox(occurred_at) WHERE published_at IS NULL;
-- Parallel workers should claim records with FOR UPDATE SKIP LOCKED.
-- Mark published only after broker ack; use a lease for a separate publish phase.
CREATE TABLE consumer_inbox (
    consumer text NOT NULL,
    event_id uuid NOT NULL,
    processed_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (consumer, event_id)
);
