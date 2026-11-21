-- Staff accounts (support agents and managers)
CREATE TABLE users (
    id serial PRIMARY KEY,
    name text NOT NULL,
    email text UNIQUE NOT NULL,
    password_hash text NOT NULL,
    role text NOT NULL CHECK (role IN ('agent', 'manager'))
);

-- Editable list of festival/public holidays excluded from working time
CREATE TABLE holidays (
    day date PRIMARY KEY,
    name text NOT NULL
);

-- Core support tickets
CREATE TABLE tickets (
    id bigserial PRIMARY KEY,
    public_token text UNIQUE NOT NULL, -- customer's secret portal link
    customer_name text NOT NULL,
    customer_email text NOT NULL,
    subject text NOT NULL,
    priority text NOT NULL CHECK (priority IN ('critical', 'medium', 'low')),
    status text NOT NULL DEFAULT 'new'
        CHECK (status IN ('new', 'open', 'waiting_customer', 'resolved', 'closed')),
    assignee_id int REFERENCES users(id),
    follows_ticket_id bigint REFERENCES tickets(id), -- links follow-up tickets after close
    waiting_since timestamptz,
    resolved_at timestamptz,
    closed_at timestamptz,
    close_reason text,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Customer-visible conversation ONLY
CREATE TABLE messages (
    id bigserial PRIMARY KEY,
    ticket_id bigint NOT NULL REFERENCES tickets(id),
    author_type text NOT NULL CHECK (author_type IN ('customer', 'agent')),
    author_id int REFERENCES users(id),
    body text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Team-only notes; never queried by public customer endpoints
CREATE TABLE internal_notes (
    id bigserial PRIMARY KEY,
    ticket_id bigint NOT NULL REFERENCES tickets(id),
    author_id int NOT NULL REFERENCES users(id),
    body text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Two SLA clocks per ticket: 'response' and 'resolution'
CREATE TABLE sla_clocks (
    ticket_id bigint NOT NULL REFERENCES tickets(id),
    kind text NOT NULL CHECK (kind IN ('response', 'resolution')),
    started_at timestamptz NOT NULL,
    target_min int NOT NULL,              -- allowed working minutes
    elapsed_min numeric NOT NULL DEFAULT 0, -- working minutes already banked before running_since
    running_since timestamptz,            -- NULL while paused or stopped
    due_at timestamptz,                   -- NULL while paused or stopped
    stopped_at timestamptz,
    breached_at timestamptz,
    PRIMARY KEY (ticket_id, kind)
);

-- Immutable audit trail of every action taken on a ticket
CREATE TABLE events (
    id bigserial PRIMARY KEY,
    ticket_id bigint NOT NULL REFERENCES tickets(id),
    at timestamptz NOT NULL DEFAULT now(),
    actor text NOT NULL,                  -- e.g. 'agent:3', 'customer', 'system'
    type text NOT NULL,
    payload jsonb NOT NULL DEFAULT '{}'
);

-- Trigger function to enforce append-only history (INC-0318)
CREATE FUNCTION forbid_change() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER events_ro
    BEFORE UPDATE OR DELETE ON events
    FOR EACH ROW EXECUTE FUNCTION forbid_change();
CREATE TRIGGER messages_ro
    BEFORE UPDATE OR DELETE ON messages
    FOR EACH ROW EXECUTE FUNCTION forbid_change();
CREATE TRIGGER notes_ro
    BEFORE UPDATE OR DELETE ON internal_notes
    FOR EACH ROW EXECUTE FUNCTION forbid_change();

CREATE TRIGGER events_nt
    BEFORE TRUNCATE ON events
    FOR EACH STATEMENT EXECUTE FUNCTION forbid_change();
CREATE TRIGGER messages_nt
    BEFORE TRUNCATE ON messages
    FOR EACH STATEMENT EXECUTE FUNCTION forbid_change();
CREATE TRIGGER notes_nt
    BEFORE TRUNCATE ON internal_notes
    FOR EACH STATEMENT EXECUTE FUNCTION forbid_change();

-- Indexes for fast agent queues, threads, audit views, and background SLA sweeps
CREATE INDEX ON tickets (assignee_id, status);
CREATE INDEX ON tickets (status);
CREATE INDEX ON messages (ticket_id, created_at);
CREATE INDEX ON internal_notes (ticket_id, created_at);
CREATE INDEX ON events (ticket_id, id);
CREATE INDEX ON events (type);
CREATE INDEX ON sla_clocks (due_at) WHERE stopped_at IS NULL;
