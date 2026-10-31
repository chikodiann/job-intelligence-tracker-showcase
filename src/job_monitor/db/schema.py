"""Database DDL definitions for SQLite persistence."""

CREATE_JOBS_TABLE = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    external_id TEXT NOT NULL,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    company_name TEXT NOT NULL,
    is_remote INTEGER NOT NULL DEFAULT 1,
    location_requirement TEXT,
    employment_type TEXT,
    salary_min REAL,
    salary_max REAL,
    salary_currency TEXT,
    salary_period TEXT,
    annualized_min_usd REAL,
    annualized_max_usd REAL,
    original_salary_text TEXT,
    category TEXT,
    tags TEXT,
    description_raw TEXT,
    description_text TEXT,
    content_hash TEXT NOT NULL,
    canonical_fingerprint TEXT NOT NULL,
    posted_at TEXT,
    fetched_at TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    last_verified_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    review_state TEXT DEFAULT 'UNREVIEWED',
    applied_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_name, external_id)
);
"""

CREATE_INDEX_FINGERPRINT = "CREATE INDEX IF NOT EXISTS idx_jobs_canonical_fingerprint ON jobs(canonical_fingerprint);"
CREATE_INDEX_CONTENT_HASH = "CREATE INDEX IF NOT EXISTS idx_jobs_content_hash ON jobs(content_hash);"
CREATE_INDEX_POSTED_AT = "CREATE INDEX IF NOT EXISTS idx_jobs_posted_at ON jobs(posted_at DESC);"
CREATE_INDEX_ANNUALIZED_SALARY = "CREATE INDEX IF NOT EXISTS idx_jobs_salary_usd ON jobs(annualized_min_usd DESC, annualized_max_usd DESC);"
CREATE_INDEX_COMPANY = "CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company_name);"
CREATE_INDEX_SOURCE = "CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source_name);"
CREATE_INDEX_URL = "CREATE INDEX IF NOT EXISTS idx_jobs_url ON jobs(url);"
CREATE_INDEX_STATUS = "CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);"
CREATE_INDEX_LOCATION = "CREATE INDEX IF NOT EXISTS idx_jobs_location ON jobs(location_requirement);"

CREATE_JOB_MATCHES_TABLE = """
CREATE TABLE IF NOT EXISTS job_matches (
    job_id TEXT PRIMARY KEY,
    overall_score REAL NOT NULL,
    keyword_score REAL NOT NULL,
    cashflow_score REAL NOT NULL,
    recency_score REAL NOT NULL,
    match_status TEXT NOT NULL DEFAULT 'NEW', -- NEW, VIEWED, SAVED, APPLIED, DISMISSED
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
);
"""

CREATE_RAW_PAYLOADS_TABLE = """
CREATE TABLE IF NOT EXISTS raw_job_payloads (
    source_name TEXT NOT NULL,
    external_id TEXT NOT NULL,
    raw_json TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY(source_name, external_id)
);
"""

CREATE_APPLICATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS applications (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'APPLIED',
    applied_at TEXT NOT NULL,
    interview_stage TEXT DEFAULT 'NONE',
    next_action TEXT,
    next_action_date TEXT,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
);
"""

CREATE_INDEX_APP_JOB_ID = "CREATE INDEX IF NOT EXISTS idx_applications_job_id ON applications(job_id);"
CREATE_INDEX_APP_STATUS = "CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);"
CREATE_INDEX_APP_APPLIED_AT = "CREATE INDEX IF NOT EXISTS idx_applications_applied_at ON applications(applied_at DESC);"

CREATE_APPLICATION_STATUS_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS application_status_history (
    id TEXT PRIMARY KEY,
    application_id TEXT NOT NULL,
    status TEXT NOT NULL,
    interview_stage TEXT DEFAULT 'NONE',
    changed_at TEXT NOT NULL,
    FOREIGN KEY(application_id) REFERENCES applications(id) ON DELETE CASCADE
);
"""

CREATE_INDEX_APP_HISTORY_APP_ID = "CREATE INDEX IF NOT EXISTS idx_app_history_app_id ON application_status_history(application_id);"
CREATE_INDEX_APP_HISTORY_CHANGED_AT = "CREATE INDEX IF NOT EXISTS idx_app_history_changed_at ON application_status_history(changed_at DESC);"

CREATE_PIPELINE_RUNS_TABLE = """
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_type TEXT NOT NULL,
    status TEXT NOT NULL,
    lagos_date TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    is_daily_morning INTEGER NOT NULL DEFAULT 0,
    jobs_fetched INTEGER NOT NULL DEFAULT 0,
    jobs_new INTEGER NOT NULL DEFAULT 0,
    jobs_updated INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_INDEX_PIPELINE_RUNS_LAGOS_DATE = "CREATE INDEX IF NOT EXISTS idx_pipeline_runs_lagos_date ON pipeline_runs(lagos_date);"
CREATE_INDEX_PIPELINE_RUNS_STARTED_AT = "CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started_at ON pipeline_runs(started_at DESC);"


