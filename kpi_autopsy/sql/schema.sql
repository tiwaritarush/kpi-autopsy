CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE applications (
    application_id TEXT PRIMARY KEY,
    application_type TEXT,
    loan_goal TEXT,
    requested_amount REAL
);

CREATE TABLE events (
    event_row INTEGER PRIMARY KEY,
    application_id TEXT NOT NULL REFERENCES applications(application_id),
    source_event_id TEXT,
    offer_id TEXT,
    activity TEXT NOT NULL,
    event_origin TEXT NOT NULL,
    lifecycle TEXT,
    occurred_at TEXT NOT NULL,
    source_timestamp TEXT NOT NULL,
    offered_amount REAL
);
