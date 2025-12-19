CREATE TABLE IF NOT EXISTS processed_events (
  topic TEXT NOT NULL,
  event_id TEXT NOT NULL,
  processed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (topic, event_id)
);

CREATE TABLE IF NOT EXISTS events (
  topic TEXT NOT NULL,
  event_id TEXT NOT NULL,
  ts TIMESTAMPTZ NOT NULL,
  source TEXT NOT NULL,
  payload JSONB NOT NULL,
  stored_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (topic, event_id)
);

CREATE TABLE IF NOT EXISTS stats (
  id INT PRIMARY KEY DEFAULT 1,
  received BIGINT NOT NULL DEFAULT 0,
  unique_processed BIGINT NOT NULL DEFAULT 0,
  duplicate_dropped BIGINT NOT NULL DEFAULT 0,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO stats(id) VALUES (1) ON CONFLICT DO NOTHING;
