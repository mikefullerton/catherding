CREATE TABLE IF NOT EXISTS health_checks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  service TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('up', 'degraded', 'down')),
  response_time_ms INTEGER NOT NULL DEFAULT 0,
  checked_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_health_checks_service ON health_checks(service);
CREATE INDEX IF NOT EXISTS idx_health_checks_checked_at ON health_checks(checked_at);
