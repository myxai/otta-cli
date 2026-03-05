CREATE TABLE IF NOT EXISTS golden_plans (
  case_key TEXT PRIMARY KEY,
  version INTEGER NOT NULL DEFAULT 1,
  template_id TEXT NOT NULL,
  plan_json TEXT NOT NULL,
  replayable INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  last_used_at TEXT,
  stats_json TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS golden_candidates (
  candidate_id TEXT PRIMARY KEY,
  case_key TEXT NOT NULL,
  template_id TEXT NOT NULL,
  plan_json TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'new', -- new|tried|promoted|invalid
  fail_reason TEXT DEFAULT '',
  created_at TEXT NOT NULL,
  tried_at TEXT
);

CREATE TABLE IF NOT EXISTS exec_runs (
  run_id TEXT PRIMARY KEY,
  case_key TEXT NOT NULL,
  route TEXT NOT NULL,
  source TEXT NOT NULL,
  success INTEGER NOT NULL,
  latency_ms INTEGER NOT NULL,
  effective_steps INTEGER NOT NULL DEFAULT 0,
  cloud_called INTEGER NOT NULL DEFAULT 0,
  fail_stage TEXT DEFAULT '',
  intent TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_exec_runs_case_key ON exec_runs(case_key);


CREATE TABLE IF NOT EXISTS capability_edges (
  src TEXT NOT NULL,
  dst TEXT NOT NULL,
  count INTEGER NOT NULL DEFAULT 0,
  last_used_at TEXT,
  PRIMARY KEY (src, dst)
);

CREATE INDEX IF NOT EXISTS idx_cap_edges_src ON capability_edges(src);
