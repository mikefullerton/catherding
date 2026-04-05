CREATE TABLE IF NOT EXISTS metrics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  service TEXT NOT NULL,
  period TEXT NOT NULL CHECK (period IN ('hourly', 'daily')),
  check_count INTEGER NOT NULL DEFAULT 0,
  up_count INTEGER NOT NULL DEFAULT 0,
  avg_response_time REAL,
  max_response_time INTEGER,
  recorded_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_metrics_service ON metrics(service);
CREATE INDEX IF NOT EXISTS idx_metrics_period ON metrics(period);
CREATE INDEX IF NOT EXISTS idx_metrics_recorded_at ON metrics(recorded_at);
