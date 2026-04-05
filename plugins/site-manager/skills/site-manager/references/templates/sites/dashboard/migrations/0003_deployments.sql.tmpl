CREATE TABLE IF NOT EXISTS deployments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  service TEXT NOT NULL,
  version TEXT,
  status TEXT NOT NULL CHECK (status IN ('deploying', 'deployed', 'failed', 'rolled_back')),
  commit_sha TEXT,
  deployed_by TEXT,
  deployed_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_deployments_service ON deployments(service);
CREATE INDEX IF NOT EXISTS idx_deployments_deployed_at ON deployments(deployed_at);
