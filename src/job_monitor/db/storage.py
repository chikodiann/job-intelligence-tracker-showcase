import json
import sqlite3
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..models.application import Application, ApplicationStatus, ApplicationStatusHistory, InterviewStage
from ..models.normalized_job import EmploymentType, NormalizedJob, SalaryPeriod
from ..models.raw_job import RawJob
from ..utils.logging import setup_logger
from ..utils.timezone import get_lagos_date_str, get_lagos_now, get_local_date_str, get_local_now
from .schema import (
    CREATE_APPLICATION_STATUS_HISTORY_TABLE,
    CREATE_APPLICATIONS_TABLE,
    CREATE_INDEX_ANNUALIZED_SALARY,
    CREATE_INDEX_APP_APPLIED_AT,
    CREATE_INDEX_APP_HISTORY_APP_ID,
    CREATE_INDEX_APP_HISTORY_CHANGED_AT,
    CREATE_INDEX_APP_JOB_ID,
    CREATE_INDEX_APP_STATUS,
    CREATE_INDEX_COMPANY,
    CREATE_INDEX_CONTENT_HASH,
    CREATE_INDEX_FINGERPRINT,
    CREATE_INDEX_LOCATION,
    CREATE_INDEX_PIPELINE_RUNS_LAGOS_DATE,
    CREATE_INDEX_PIPELINE_RUNS_STARTED_AT,
    CREATE_INDEX_POSTED_AT,
    CREATE_INDEX_SOURCE,
    CREATE_INDEX_STATUS,
    CREATE_INDEX_URL,
    CREATE_JOB_MATCHES_TABLE,
    CREATE_JOBS_TABLE,
    CREATE_PIPELINE_RUNS_TABLE,
    CREATE_RAW_PAYLOADS_TABLE,
)

logger = setup_logger("storage")


class JobStorage:
    """SQLite database storage manager for jobs, raw payloads, match records, applications, and status history."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None or db_path == "data/jobs.db":
            from ..utils.paths import AppPaths
            db_path = AppPaths.get_database_path(default_db=db_path)
        self.db_path = db_path
        self._mem_conn: Optional[sqlite3.Connection] = None
        self._ensure_db_dir()
        if self.db_path == ":memory:":
            self._mem_conn = sqlite3.connect(":memory:")
            self._mem_conn.row_factory = sqlite3.Row
        self.init_db()

    def _ensure_db_dir(self) -> None:
        """Ensures directory for database file exists."""
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        """Returns a configured SQLite connection."""
        if self._mem_conn is not None:
            return self._mem_conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Initializes tables and indexes, executing schema migrations as needed."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(CREATE_JOBS_TABLE)
            cursor.execute(CREATE_INDEX_FINGERPRINT)
            cursor.execute(CREATE_INDEX_CONTENT_HASH)
            cursor.execute(CREATE_INDEX_POSTED_AT)
            cursor.execute(CREATE_INDEX_ANNUALIZED_SALARY)
            cursor.execute(CREATE_INDEX_COMPANY)
            cursor.execute(CREATE_INDEX_SOURCE)
            cursor.execute(CREATE_INDEX_URL)
            cursor.execute(CREATE_INDEX_STATUS)
            cursor.execute(CREATE_INDEX_LOCATION)
            cursor.execute(CREATE_JOB_MATCHES_TABLE)
            cursor.execute(CREATE_RAW_PAYLOADS_TABLE)
            cursor.execute(CREATE_APPLICATIONS_TABLE)
            cursor.execute(CREATE_INDEX_APP_JOB_ID)
            cursor.execute(CREATE_INDEX_APP_STATUS)
            cursor.execute(CREATE_INDEX_APP_APPLIED_AT)
            cursor.execute(CREATE_APPLICATION_STATUS_HISTORY_TABLE)
            cursor.execute(CREATE_INDEX_APP_HISTORY_APP_ID)
            cursor.execute(CREATE_INDEX_APP_HISTORY_CHANGED_AT)
            cursor.execute(CREATE_PIPELINE_RUNS_TABLE)
            cursor.execute(CREATE_INDEX_PIPELINE_RUNS_LAGOS_DATE)
            cursor.execute(CREATE_INDEX_PIPELINE_RUNS_STARTED_AT)

            # Migration 1: Add review_state and applied_at columns to jobs table if missing
            cursor.execute("PRAGMA table_info(jobs)")
            cols = [r["name"] for r in cursor.fetchall()]
            if "review_state" not in cols:
                cursor.execute("ALTER TABLE jobs ADD COLUMN review_state TEXT DEFAULT 'UNREVIEWED'")
            if "applied_at" not in cols:
                cursor.execute("ALTER TABLE jobs ADD COLUMN applied_at TEXT")

            # Migration 2: Auto-migrate any existing jobs.applied_at values into applications table
            cursor.execute("SELECT id, applied_at FROM jobs WHERE applied_at IS NOT NULL AND applied_at != ''")
            jobs_with_applied = cursor.fetchall()
            for r in jobs_with_applied:
                j_id = r["id"]
                applied_ts = r["applied_at"]
                cursor.execute("SELECT 1 FROM applications WHERE job_id = ?", (j_id,))
                if not cursor.fetchone():
                    app_uuid = str(uuid.uuid4())
                    cursor.execute(
                        "INSERT INTO applications (id, job_id, status, applied_at, interview_stage) VALUES (?, ?, 'APPLIED', ?, 'NONE')",
                        (app_uuid, j_id, applied_ts),
                    )

            # Migration 3: Auto-create baseline history entries for existing applications without history
            cursor.execute("SELECT id, status, interview_stage, applied_at, created_at FROM applications")
            existing_apps = cursor.fetchall()
            for app_row in existing_apps:
                app_id = app_row["id"]
                cursor.execute("SELECT 1 FROM application_status_history WHERE application_id = ?", (app_id,))
                if not cursor.fetchone():
                    hist_id = str(uuid.uuid4())
                    changed_at = app_row["applied_at"] or app_row["created_at"] or datetime.now(timezone.utc).isoformat()
                    cursor.execute(
                        "INSERT INTO application_status_history (id, application_id, status, interview_stage, changed_at) VALUES (?, ?, ?, ?, ?)",
                        (hist_id, app_id, app_row["status"], app_row["interview_stage"] or "NONE", changed_at),
                    )

            conn.commit()


    def save_raw_payload(self, raw_job: RawJob) -> bool:
        """Persists raw vendor job payload."""
        query = """
        INSERT OR REPLACE INTO raw_job_payloads (source_name, external_id, raw_json, fetched_at)
        VALUES (?, ?, ?, ?)
        """
        with self.get_connection() as conn:
            conn.cursor().execute(
                query,
                (
                    raw_job.source_name,
                    raw_job.external_id,
                    json.dumps(raw_job.payload),
                    raw_job.fetched_at.isoformat(),
                ),
            )
            conn.commit()
            return True

    def get_raw_payload(self, source_name: str, external_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves raw json payload for source & external id."""
        query = "SELECT raw_json FROM raw_job_payloads WHERE source_name = ? AND external_id = ?"
        with self.get_connection() as conn:
            row = conn.cursor().execute(query, (source_name, external_id)).fetchone()
            if row:
                return json.loads(row["raw_json"])
            return None

    def save_normalized_job(self, job: NormalizedJob) -> Tuple[str, bool]:
        """Saves or updates a normalized job record."""
        existing = self.get_job_by_source_and_ext_id(job.source_name, job.external_id)
        is_new = existing is None
        job_id = existing.id if existing else (job.id or str(uuid.uuid4()))
        first_seen = existing.first_seen_at.isoformat() if existing else job.first_seen_at.isoformat()
        review_state = existing.review_state if existing else job.review_state
        applied_at_str = existing.applied_at.isoformat() if (existing and existing.applied_at) else (job.applied_at.isoformat() if job.applied_at else None)

        query = """
        INSERT INTO jobs (
            id, source_name, external_id, url, title, company_name, is_remote,
            location_requirement, employment_type, salary_min, salary_max,
            salary_currency, salary_period, annualized_min_usd, annualized_max_usd,
            original_salary_text, category, tags, description_raw, description_text,
            content_hash, canonical_fingerprint, posted_at, fetched_at,
            first_seen_at, last_seen_at, last_verified_at, status, review_state, applied_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_name, external_id) DO UPDATE SET
            title=excluded.title,
            company_name=excluded.company_name,
            url=excluded.url,
            location_requirement=excluded.location_requirement,
            employment_type=excluded.employment_type,
            salary_min=excluded.salary_min,
            salary_max=excluded.salary_max,
            salary_currency=excluded.salary_currency,
            salary_period=excluded.salary_period,
            annualized_min_usd=excluded.annualized_min_usd,
            annualized_max_usd=excluded.annualized_max_usd,
            original_salary_text=excluded.original_salary_text,
            category=excluded.category,
            tags=excluded.tags,
            description_raw=excluded.description_raw,
            description_text=excluded.description_text,
            content_hash=excluded.content_hash,
            canonical_fingerprint=excluded.canonical_fingerprint,
            fetched_at=excluded.fetched_at,
            last_seen_at=excluded.last_seen_at,
            last_verified_at=excluded.last_verified_at,
            status=excluded.status
        """
        with self.get_connection() as conn:
            conn.cursor().execute(
                query,
                (
                    job_id,
                    job.source_name,
                    job.external_id,
                    job.url,
                    job.title,
                    job.company_name,
                    1 if job.is_remote else 0,
                    job.location_requirement,
                    job.employment_type.value,
                    job.salary_min,
                    job.salary_max,
                    job.salary_currency,
                    job.salary_period.value,
                    job.annualized_min_usd,
                    job.annualized_max_usd,
                    job.original_salary_text,
                    job.category,
                    json.dumps(job.tags),
                    job.description_raw,
                    job.description_text,
                    job.content_hash,
                    job.canonical_fingerprint,
                    job.posted_at.isoformat() if job.posted_at else None,
                    job.fetched_at.isoformat(),
                    first_seen,
                    job.last_seen_at.isoformat(),
                    job.last_verified_at.isoformat(),
                    job.status,
                    review_state,
                    applied_at_str,
                ),
            )
            conn.commit()
        return job_id, is_new

    def update_review_state(self, job_id: str, review_state: str) -> bool:
        """Updates lightweight review_state (UNREVIEWED, REVIEWING, DISMISSED) for a job."""
        query = "UPDATE jobs SET review_state = ? WHERE id = ?"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (review_state, job_id))
            conn.commit()
            return cursor.rowcount > 0

    def mark_as_applied(self, job_id: str, applied_at: Optional[datetime] = None) -> bool:
        """Records user intent/timestamp that an application was explicitly submitted and creates Application record."""
        if applied_at is None:
            applied_at = datetime.now(timezone.utc)
        iso_str = applied_at.isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 1. Update jobs table
            cursor.execute("UPDATE jobs SET applied_at = ? WHERE id = ?", (iso_str, job_id))

            # 2. Insert into applications table if not already present
            cursor.execute("SELECT 1 FROM applications WHERE job_id = ?", (job_id,))
            if not cursor.fetchone():
                app_id = str(uuid.uuid4())
                cursor.execute(
                    "INSERT INTO applications (id, job_id, status, applied_at, interview_stage) VALUES (?, ?, 'APPLIED', ?, 'NONE')",
                    (app_id, job_id, iso_str),
                )
                # 3. Log initial status history
                hist_id = str(uuid.uuid4())
                cursor.execute(
                    "INSERT INTO application_status_history (id, application_id, status, interview_stage, changed_at) VALUES (?, ?, 'APPLIED', 'NONE', ?)",
                    (hist_id, app_id, iso_str),
                )

            conn.commit()
            return True

    # --- Application Entity Storage Methods ---

    def create_application(self, application: Application) -> Tuple[Application, bool]:
        """Creates a new Application record linked to a job. Prevents duplicates."""
        existing = self.get_application_by_job_id(application.job_id)
        if existing:
            return existing, False

        app_id = application.id or str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        applied_iso = application.applied_at.isoformat() if application.applied_at else now_iso

        query = """
        INSERT INTO applications (
            id, job_id, status, applied_at, interview_stage, next_action,
            next_action_date, notes, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                query,
                (
                    app_id,
                    application.job_id,
                    application.status.value,
                    applied_iso,
                    application.interview_stage.value,
                    application.next_action,
                    application.next_action_date,
                    application.notes,
                    now_iso,
                    now_iso,
                ),
            )
            # Log initial status history
            hist_id = str(uuid.uuid4())
            cursor.execute(
                "INSERT INTO application_status_history (id, application_id, status, interview_stage, changed_at) VALUES (?, ?, ?, ?, ?)",
                (hist_id, app_id, application.status.value, application.interview_stage.value, applied_iso),
            )
            # Sync jobs.applied_at
            cursor.execute("UPDATE jobs SET applied_at = ? WHERE id = ?", (applied_iso, application.job_id))
            conn.commit()

        created = self.get_application_by_id(app_id)
        return created or application, True

    def get_application_by_id(self, app_id: str) -> Optional[Application]:
        """Retrieves Application record by ID."""
        query = "SELECT * FROM applications WHERE id = ?"
        with self.get_connection() as conn:
            row = conn.cursor().execute(query, (app_id,)).fetchone()
            if not row:
                return None
            return self._row_to_application(row)

    def get_application_by_job_id(self, job_id: str) -> Optional[Application]:
        """Retrieves Application record by job_id."""
        query = "SELECT * FROM applications WHERE job_id = ?"
        with self.get_connection() as conn:
            row = conn.cursor().execute(query, (job_id,)).fetchone()
            if not row:
                return None
            return self._row_to_application(row)

    def get_status_history(self, application_id: str) -> List[ApplicationStatusHistory]:
        """Retrieves historical status transition events for an application."""
        query = "SELECT * FROM application_status_history WHERE application_id = ? ORDER BY changed_at ASC"
        with self.get_connection() as conn:
            rows = conn.cursor().execute(query, (application_id,)).fetchall()
            results = []
            for r in rows:
                st = ApplicationStatus(r["status"]) if r["status"] in ApplicationStatus.__members__ else ApplicationStatus.APPLIED
                stg = InterviewStage(r["interview_stage"]) if r["interview_stage"] in InterviewStage.__members__ else InterviewStage.NONE
                results.append(ApplicationStatusHistory(
                    id=r["id"],
                    application_id=r["application_id"],
                    status=st,
                    interview_stage=stg,
                    changed_at=datetime.fromisoformat(r["changed_at"]),
                ))
            return results

    def update_application(
        self,
        app_id: str,
        status: Optional[ApplicationStatus] = None,
        interview_stage: Optional[InterviewStage] = None,
        next_action: Optional[str] = None,
        next_action_date: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[Application]:
        """Updates an existing application's status, interview stage, next action, or notes."""
        app = self.get_application_by_id(app_id)
        if not app:
            return None

        new_status = status.value if status else app.status.value
        new_stage = interview_stage.value if interview_stage else app.interview_stage.value
        new_action = next_action if next_action is not None else app.next_action
        new_action_date = next_action_date if next_action_date is not None else app.next_action_date
        new_notes = notes if notes is not None else app.notes
        now_iso = datetime.now(timezone.utc).isoformat()

        status_changed = (status is not None and status.value != app.status.value)
        stage_changed = (interview_stage is not None and interview_stage.value != app.interview_stage.value)

        query = """
        UPDATE applications SET
            status = ?,
            interview_stage = ?,
            next_action = ?,
            next_action_date = ?,
            notes = ?,
            updated_at = ?
        WHERE id = ?
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                query,
                (new_status, new_stage, new_action, new_action_date, new_notes, now_iso, app_id),
            )
            if status_changed or stage_changed:
                hist_id = str(uuid.uuid4())
                cursor.execute(
                    "INSERT INTO application_status_history (id, application_id, status, interview_stage, changed_at) VALUES (?, ?, ?, ?, ?)",
                    (hist_id, app_id, new_status, new_stage, now_iso),
                )
            conn.commit()

        return self.get_application_by_id(app_id)

    def list_applications(self, status: Optional[str] = None, limit: int = 500) -> List[Application]:
        """Lists application records, optionally filtered by status."""
        if status and status.upper() != "ALL":
            query = "SELECT * FROM applications WHERE status = ? ORDER BY applied_at DESC LIMIT ?"
            args = (status.upper(), limit)
        else:
            query = "SELECT * FROM applications ORDER BY applied_at DESC LIMIT ?"
            args = (limit,)

        with self.get_connection() as conn:
            rows = conn.cursor().execute(query, args).fetchall()
            return [self._row_to_application(r) for r in rows]

    def count_applications_summary(self) -> Dict[str, int]:
        """Computes summary metrics from the applications table for dashboard cards."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            total = cursor.execute("SELECT COUNT(*) as cnt FROM applications").fetchone()["cnt"]
            
            # Apps applied in last 7 days
            week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            this_week = cursor.execute("SELECT COUNT(*) as cnt FROM applications WHERE applied_at >= ?", (week_ago,)).fetchone()["cnt"]

            awaiting = cursor.execute("SELECT COUNT(*) as cnt FROM applications WHERE status NOT IN ('REJECTED', 'WITHDRAWN', 'ACCEPTED', 'OFFER')").fetchone()["cnt"]
            interviews = cursor.execute("SELECT COUNT(*) as cnt FROM applications WHERE status = 'INTERVIEW'").fetchone()["cnt"]
            offers = cursor.execute("SELECT COUNT(*) as cnt FROM applications WHERE status = 'OFFER'").fetchone()["cnt"]
            rejections = cursor.execute("SELECT COUNT(*) as cnt FROM applications WHERE status = 'REJECTED'").fetchone()["cnt"]

            return {
                "total_applications": total,
                "applications_this_week": this_week,
                "awaiting_response": awaiting,
                "interviews": interviews,
                "offers": offers,
                "rejections": rejections,
            }

    # --- Phase 8 Analytics Methods ---

    def get_analytics_summary(self) -> Dict[str, Any]:
        """Calculates top-level metrics for Application Analytics."""
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)
        days_7_start = now - timedelta(days=7)
        days_30_start = now - timedelta(days=30)

        today_iso = today_start.isoformat()
        yesterday_iso = yesterday_start.isoformat()
        days_7_iso = days_7_start.isoformat()
        days_30_iso = days_30_start.isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            total = cursor.execute("SELECT COUNT(*) as cnt FROM applications").fetchone()["cnt"]
            today = cursor.execute("SELECT COUNT(*) as cnt FROM applications WHERE applied_at >= ?", (today_iso,)).fetchone()["cnt"]
            yesterday = cursor.execute("SELECT COUNT(*) as cnt FROM applications WHERE applied_at >= ? AND applied_at < ?", (yesterday_iso, today_iso)).fetchone()["cnt"]
            last_7 = cursor.execute("SELECT COUNT(*) as cnt FROM applications WHERE applied_at >= ?", (days_7_iso,)).fetchone()["cnt"]
            last_30 = cursor.execute("SELECT COUNT(*) as cnt FROM applications WHERE applied_at >= ?", (days_30_iso,)).fetchone()["cnt"]

            # Status counts
            applied = cursor.execute("SELECT COUNT(*) as cnt FROM applications WHERE status = 'APPLIED'").fetchone()["cnt"]
            assessments = cursor.execute("SELECT COUNT(*) as cnt FROM applications WHERE status = 'ASSESSMENT'").fetchone()["cnt"]
            interviews = cursor.execute("SELECT COUNT(*) as cnt FROM applications WHERE status = 'INTERVIEW'").fetchone()["cnt"]
            offers = cursor.execute("SELECT COUNT(*) as cnt FROM applications WHERE status = 'OFFER'").fetchone()["cnt"]
            rejections = cursor.execute("SELECT COUNT(*) as cnt FROM applications WHERE status = 'REJECTED'").fetchone()["cnt"]
            withdrawn = cursor.execute("SELECT COUNT(*) as cnt FROM applications WHERE status = 'WITHDRAWN'").fetchone()["cnt"]
            accepted = cursor.execute("SELECT COUNT(*) as cnt FROM applications WHERE status = 'ACCEPTED'").fetchone()["cnt"]

            # Awaiting Response: active applications that have NOT reached REJECTED, WITHDRAWN, ACCEPTED, or OFFER
            awaiting = cursor.execute(
                "SELECT COUNT(*) as cnt FROM applications WHERE status NOT IN ('REJECTED', 'WITHDRAWN', 'ACCEPTED', 'OFFER')"
            ).fetchone()["cnt"]

            return {
                "total_applications": total,
                "applications_today": today,
                "applications_yesterday": yesterday,
                "applications_7_days": last_7,
                "applications_30_days": last_30,
                "awaiting_response": awaiting,
                "applied": applied,
                "assessments": assessments,
                "interviews": interviews,
                "offers": offers,
                "rejections": rejections,
                "withdrawn": withdrawn,
                "accepted": accepted,
            }

    def get_daily_analytics(self, days: int = 7) -> List[Dict[str, Any]]:
        """Generates timeline of daily application counts for the given number of days."""
        now = datetime.now(timezone.utc)
        dates_list = [(now - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days - 1, -1, -1)]
        start_date_iso = (now - timedelta(days=days)).isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            rows = cursor.execute(
                "SELECT date(applied_at) as app_date, COUNT(*) as cnt FROM applications WHERE applied_at >= ? GROUP BY date(applied_at)",
                (start_date_iso,)
            ).fetchall()
            counts_by_date = {r["app_date"]: r["cnt"] for r in rows if r["app_date"]}

        return [{"date": d, "count": counts_by_date.get(d, 0)} for d in dates_list]

    def get_weekly_summary(self) -> Dict[str, Any]:
        """Calculates weekly application activity and volume comparison with previous week."""
        now = datetime.now(timezone.utc)
        week_1_start = (now - timedelta(days=7)).isoformat()
        week_2_start = (now - timedelta(days=14)).isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            # This week
            tw_total = cursor.execute("SELECT COUNT(*) as cnt FROM applications WHERE applied_at >= ?", (week_1_start,)).fetchone()["cnt"]
            tw_assess = cursor.execute("SELECT COUNT(*) as cnt FROM applications WHERE applied_at >= ? AND status = 'ASSESSMENT'", (week_1_start,)).fetchone()["cnt"]
            tw_interviews = cursor.execute("SELECT COUNT(*) as cnt FROM applications WHERE applied_at >= ? AND status = 'INTERVIEW'", (week_1_start,)).fetchone()["cnt"]
            tw_offers = cursor.execute("SELECT COUNT(*) as cnt FROM applications WHERE applied_at >= ? AND status = 'OFFER'", (week_1_start,)).fetchone()["cnt"]
            tw_rejections = cursor.execute("SELECT COUNT(*) as cnt FROM applications WHERE applied_at >= ? AND status = 'REJECTED'", (week_1_start,)).fetchone()["cnt"]

            # Previous week
            pw_total = cursor.execute("SELECT COUNT(*) as cnt FROM applications WHERE applied_at >= ? AND applied_at < ?", (week_2_start, week_1_start)).fetchone()["cnt"]
            pw_assess = cursor.execute("SELECT COUNT(*) as cnt FROM applications WHERE applied_at >= ? AND applied_at < ? AND status = 'ASSESSMENT'", (week_2_start, week_1_start)).fetchone()["cnt"]
            pw_interviews = cursor.execute("SELECT COUNT(*) as cnt FROM applications WHERE applied_at >= ? AND applied_at < ? AND status = 'INTERVIEW'", (week_2_start, week_1_start)).fetchone()["cnt"]
            pw_offers = cursor.execute("SELECT COUNT(*) as cnt FROM applications WHERE applied_at >= ? AND applied_at < ? AND status = 'OFFER'", (week_2_start, week_1_start)).fetchone()["cnt"]
            pw_rejections = cursor.execute("SELECT COUNT(*) as cnt FROM applications WHERE applied_at >= ? AND applied_at < ? AND status = 'REJECTED'", (week_2_start, week_1_start)).fetchone()["cnt"]

            change_pct = None
            if pw_total > 0:
                change_pct = round(((tw_total - pw_total) / pw_total) * 100.0, 1)

            return {
                "this_week": {
                    "applications": tw_total,
                    "assessments": tw_assess,
                    "interviews": tw_interviews,
                    "offers": tw_offers,
                    "rejections": tw_rejections,
                },
                "previous_week": {
                    "applications": pw_total,
                    "assessments": pw_assess,
                    "interviews": pw_interviews,
                    "offers": pw_offers,
                    "rejections": pw_rejections,
                },
                "volume_change_pct": change_pct,
                "has_sufficient_history": pw_total > 0 or tw_total > 0
            }

    def get_funnel_analytics(self) -> Dict[str, Any]:
        """Calculates funnel progression and conversion rates based on application_status_history and applications."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            total_apps = cursor.execute("SELECT COUNT(*) as cnt FROM applications").fetchone()["cnt"]

            assessments = cursor.execute("""
                SELECT COUNT(DISTINCT application_id) as cnt FROM application_status_history
                WHERE status IN ('ASSESSMENT', 'INTERVIEW', 'OFFER', 'ACCEPTED')
            """).fetchone()["cnt"]

            interviews = cursor.execute("""
                SELECT COUNT(DISTINCT application_id) as cnt FROM application_status_history
                WHERE status IN ('INTERVIEW', 'OFFER', 'ACCEPTED')
            """).fetchone()["cnt"]

            offers = cursor.execute("""
                SELECT COUNT(DISTINCT application_id) as cnt FROM application_status_history
                WHERE status IN ('OFFER', 'ACCEPTED')
            """).fetchone()["cnt"]

            accepted = cursor.execute("""
                SELECT COUNT(DISTINCT application_id) as cnt FROM application_status_history
                WHERE status = 'ACCEPTED'
            """).fetchone()["cnt"]

            # Conversion Rates
            app_to_assess = round((assessments / total_apps * 100.0), 1) if total_apps > 0 else 0.0
            app_to_interview = round((interviews / total_apps * 100.0), 1) if total_apps > 0 else 0.0
            app_to_offer = round((offers / total_apps * 100.0), 1) if total_apps > 0 else 0.0
            interview_to_offer = round((offers / interviews * 100.0), 1) if interviews > 0 else None
            offer_to_accepted = round((accepted / offers * 100.0), 1) if offers > 0 else None

            # Formatted text strings for UI display
            fmt_app_assess = f"{app_to_assess}% ({assessments} of {total_apps} applications)" if total_apps > 0 else "Historical transition data unavailable"
            fmt_app_interview = f"{app_to_interview}% ({interviews} of {total_apps} applications)" if total_apps > 0 else "Historical transition data unavailable"
            fmt_app_offer = f"{app_to_offer}% ({offers} of {total_apps} applications)" if total_apps > 0 else "Historical transition data unavailable"
            fmt_interview_offer = f"{interview_to_offer}% ({offers} of {interviews} interviews)" if interviews > 0 else "Historical transition data unavailable"
            fmt_offer_accepted = f"{offer_to_accepted}% ({accepted} of {offers} offers)" if offers > 0 else "Historical transition data unavailable"

            return {
                "funnel_counts": {
                    "applications": total_apps,
                    "assessments": assessments,
                    "interviews": interviews,
                    "offers": offers,
                    "accepted": accepted,
                },
                "conversion_rates": {
                    "app_to_assessment_pct": app_to_assess,
                    "app_to_interview_pct": app_to_interview,
                    "app_to_offer_pct": app_to_offer,
                    "interview_to_offer_pct": interview_to_offer,
                    "offer_to_accepted_pct": offer_to_accepted,
                },
                "formatted_rates": {
                    "app_to_assessment": fmt_app_assess,
                    "app_to_interview": fmt_app_interview,
                    "app_to_offer": fmt_app_offer,
                    "interview_to_offer": fmt_interview_offer,
                    "offer_to_accepted": fmt_offer_accepted,
                }
            }

    def get_source_analytics(self) -> List[Dict[str, Any]]:
        """Calculates application outcome performance grouped by job source."""
        query = """
        SELECT
            j.source_name as source_name,
            COUNT(a.id) as applications,
            SUM(CASE WHEN a.status = 'INTERVIEW' OR h.has_interview = 1 THEN 1 ELSE 0 END) as interviews,
            SUM(CASE WHEN a.status = 'OFFER' OR a.status = 'ACCEPTED' OR h.has_offer = 1 THEN 1 ELSE 0 END) as offers,
            SUM(CASE WHEN a.status = 'REJECTED' THEN 1 ELSE 0 END) as rejections
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        LEFT JOIN (
            SELECT
                application_id,
                MAX(CASE WHEN status IN ('INTERVIEW', 'OFFER', 'ACCEPTED') THEN 1 ELSE 0 END) as has_interview,
                MAX(CASE WHEN status IN ('OFFER', 'ACCEPTED') THEN 1 ELSE 0 END) as has_offer
            FROM application_status_history
            GROUP BY application_id
        ) h ON a.id = h.application_id
        GROUP BY j.source_name
        ORDER BY applications DESC
        """
        with self.get_connection() as conn:
            rows = conn.cursor().execute(query).fetchall()
            results = []
            for r in rows:
                apps = r["applications"]
                interviews = r["interviews"]
                rate = round((interviews / apps * 100.0), 1) if apps > 0 else 0.0
                results.append({
                    "source_name": r["source_name"],
                    "applications": apps,
                    "interviews": interviews,
                    "offers": r["offers"],
                    "rejections": r["rejections"],
                    "interview_rate_pct": rate,
                })
            return results

    def get_category_analytics(self) -> List[Dict[str, Any]]:
        """Calculates application outcomes grouped by job category."""
        query = """
        SELECT
            COALESCE(NULLIF(j.category, ''), 'Software Engineering') as category_name,
            COUNT(a.id) as applications,
            SUM(CASE WHEN a.status = 'ASSESSMENT' OR h.has_assess = 1 THEN 1 ELSE 0 END) as assessments,
            SUM(CASE WHEN a.status = 'INTERVIEW' OR h.has_interview = 1 THEN 1 ELSE 0 END) as interviews,
            SUM(CASE WHEN a.status = 'OFFER' OR a.status = 'ACCEPTED' OR h.has_offer = 1 THEN 1 ELSE 0 END) as offers,
            SUM(CASE WHEN a.status = 'REJECTED' THEN 1 ELSE 0 END) as rejections
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        LEFT JOIN (
            SELECT
                application_id,
                MAX(CASE WHEN status IN ('ASSESSMENT', 'INTERVIEW', 'OFFER', 'ACCEPTED') THEN 1 ELSE 0 END) as has_assess,
                MAX(CASE WHEN status IN ('INTERVIEW', 'OFFER', 'ACCEPTED') THEN 1 ELSE 0 END) as has_interview,
                MAX(CASE WHEN status IN ('OFFER', 'ACCEPTED') THEN 1 ELSE 0 END) as has_offer
            FROM application_status_history
            GROUP BY application_id
        ) h ON a.id = h.application_id
        GROUP BY category_name
        ORDER BY applications DESC
        """
        with self.get_connection() as conn:
            rows = conn.cursor().execute(query).fetchall()
            return [{
                "category": r["category_name"],
                "applications": r["applications"],
                "assessments": r["assessments"],
                "interviews": r["interviews"],
                "offers": r["offers"],
                "rejections": r["rejections"],
            } for r in rows]

    def get_next_actions_analytics(self) -> Dict[str, List[Dict[str, Any]]]:
        """Categorizes upcoming next actions into Overdue, Due Today, and Due in Next 7 Days."""
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        next_7_str = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")

        query = """
        SELECT a.*, j.title as job_title, j.company_name as company_name
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        WHERE (a.next_action IS NOT NULL AND a.next_action != '')
           OR (a.next_action_date IS NOT NULL AND a.next_action_date != '')
        ORDER BY a.next_action_date ASC
        """
        with self.get_connection() as conn:
            rows = conn.cursor().execute(query).fetchall()
            overdue = []
            due_today = []
            due_next_7 = []

            for r in rows:
                item = {
                    "id": r["id"],
                    "job_id": r["job_id"],
                    "job_title": r["job_title"],
                    "company_name": r["company_name"],
                    "status": r["status"],
                    "interview_stage": r["interview_stage"] or "NONE",
                    "next_action": r["next_action"] or "Action required",
                    "next_action_date": r["next_action_date"] or "",
                }
                date_val = r["next_action_date"]
                if not date_val:
                    due_next_7.append(item)
                elif date_val < today_str:
                    overdue.append(item)
                elif date_val == today_str:
                    due_today.append(item)
                elif date_val <= next_7_str:
                    due_next_7.append(item)

            return {
                "overdue": overdue,
                "due_today": due_today,
                "due_next_7_days": due_next_7,
            }

    def get_full_analytics(self) -> Dict[str, Any]:
        """Consolidates all analytics sub-metrics into a single dictionary."""
        return {
            "summary": self.get_analytics_summary(),
            "daily_activity_7d": self.get_daily_analytics(days=7),
            "daily_activity_30d": self.get_daily_analytics(days=30),
            "weekly_summary": self.get_weekly_summary(),
            "funnel": self.get_funnel_analytics(),
            "sources": self.get_source_analytics(),
            "categories": self.get_category_analytics(),
            "next_actions": self.get_next_actions_analytics(),
        }


    def _row_to_application(self, row: sqlite3.Row) -> Application:
        """Converts SQLite Row to Application model."""
        keys = row.keys()
        return Application(
            id=row["id"],
            job_id=row["job_id"],
            status=ApplicationStatus(row["status"]) if row["status"] in ApplicationStatus.__members__ else ApplicationStatus.APPLIED,
            applied_at=datetime.fromisoformat(row["applied_at"]),
            interview_stage=InterviewStage(row["interview_stage"]) if row["interview_stage"] in InterviewStage.__members__ else InterviewStage.NONE,
            next_action=row["next_action"] if "next_action" in keys else None,
            next_action_date=row["next_action_date"] if "next_action_date" in keys else None,
            notes=row["notes"] if "notes" in keys else None,
            created_at=datetime.fromisoformat(row["created_at"]) if "created_at" in keys and row["created_at"] else datetime.now(timezone.utc),
            updated_at=datetime.fromisoformat(row["updated_at"]) if "updated_at" in keys and row["updated_at"] else datetime.now(timezone.utc),
        )

    # --- Job Storage Methods ---

    def get_job_by_source_and_ext_id(self, source_name: str, external_id: str) -> Optional[NormalizedJob]:
        """Retrieves job by source and external ID."""
        query = "SELECT * FROM jobs WHERE source_name = ? AND external_id = ?"
        with self.get_connection() as conn:
            row = conn.cursor().execute(query, (source_name, external_id)).fetchone()
            if not row:
                return None
            return self._row_to_normalized_job(row)

    def get_job_by_id(self, job_id: str) -> Optional[NormalizedJob]:
        """Retrieves normalized job by primary key ID."""
        query = "SELECT * FROM jobs WHERE id = ?"
        with self.get_connection() as conn:
            row = conn.cursor().execute(query, (job_id,)).fetchone()
            if not row:
                return None
            return self._row_to_normalized_job(row)

    def get_job_by_url(self, url: str) -> Optional[NormalizedJob]:
        """Retrieves job by application URL."""
        query = "SELECT * FROM jobs WHERE url = ? LIMIT 1"
        with self.get_connection() as conn:
            row = conn.cursor().execute(query, (url,)).fetchone()
            if not row:
                return None
            return self._row_to_normalized_job(row)

    def get_job_by_fingerprint(self, canonical_fingerprint: str) -> Optional[NormalizedJob]:
        """Retrieves job by canonical fingerprint."""
        query = "SELECT * FROM jobs WHERE canonical_fingerprint = ? LIMIT 1"
        with self.get_connection() as conn:
            row = conn.cursor().execute(query, (canonical_fingerprint,)).fetchone()
            if not row:
                return None
            return self._row_to_normalized_job(row)

    def get_job_by_content_hash(self, content_hash: str) -> Optional[NormalizedJob]:
        """Retrieves job by content SHA256 hash."""
        query = "SELECT * FROM jobs WHERE content_hash = ? LIMIT 1"
        with self.get_connection() as conn:
            row = conn.cursor().execute(query, (content_hash,)).fetchone()
            if not row:
                return None
            return self._row_to_normalized_job(row)

    def exists_by_fingerprint_or_hash(self, fingerprint: str, content_hash: str) -> bool:
        """Checks if job with identical fingerprint or content hash exists."""
        query = "SELECT 1 FROM jobs WHERE canonical_fingerprint = ? OR content_hash = ? LIMIT 1"
        with self.get_connection() as conn:
            row = conn.cursor().execute(query, (fingerprint, content_hash)).fetchone()
            return row is not None

    def update_job_seen(self, job_id: str, seen_at: datetime) -> None:
        """Updates last_seen_at and last_verified_at for a known job."""
        query = "UPDATE jobs SET last_seen_at = ?, last_verified_at = ? WHERE id = ?"
        iso_str = seen_at.isoformat()
        with self.get_connection() as conn:
            conn.cursor().execute(query, (iso_str, iso_str, job_id))
            conn.commit()

    def count_jobs(self) -> int:
        """Returns total count of stored jobs."""
        with self.get_connection() as conn:
            row = conn.cursor().execute("SELECT COUNT(*) as cnt FROM jobs").fetchone()
            return row["cnt"]

    def list_jobs(self, limit: int = 1000) -> List[NormalizedJob]:
        """Returns list of recent jobs."""
        query = "SELECT * FROM jobs ORDER BY posted_at DESC, fetched_at DESC LIMIT ?"
        with self.get_connection() as conn:
            rows = conn.cursor().execute(query, (limit,)).fetchall()
            return [self._row_to_normalized_job(r) for r in rows]

    def _row_to_normalized_job(self, row: sqlite3.Row) -> NormalizedJob:
        """Converts sqlite Row to NormalizedJob model."""
        keys = row.keys()
        return NormalizedJob(
            id=row["id"],
            source_name=row["source_name"],
            external_id=row["external_id"],
            url=row["url"],
            title=row["title"],
            company_name=row["company_name"],
            is_remote=bool(row["is_remote"]),
            location_requirement=row["location_requirement"],
            employment_type=EmploymentType(row["employment_type"]) if row["employment_type"] else EmploymentType.UNKNOWN,
            salary_min=row["salary_min"],
            salary_max=row["salary_max"],
            salary_currency=row["salary_currency"],
            salary_period=SalaryPeriod(row["salary_period"]) if row["salary_period"] else SalaryPeriod.UNKNOWN,
            annualized_min_usd=row["annualized_min_usd"],
            annualized_max_usd=row["annualized_max_usd"],
            original_salary_text=row["original_salary_text"] if "original_salary_text" in keys else None,
            category=row["category"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            description_raw=row["description_raw"],
            description_text=row["description_text"],
            content_hash=row["content_hash"],
            canonical_fingerprint=row["canonical_fingerprint"],
            posted_at=datetime.fromisoformat(row["posted_at"]) if row["posted_at"] else None,
            fetched_at=datetime.fromisoformat(row["fetched_at"]),
            first_seen_at=datetime.fromisoformat(row["first_seen_at"]) if "first_seen_at" in keys and row["first_seen_at"] else datetime.fromisoformat(row["fetched_at"]),
            last_seen_at=datetime.fromisoformat(row["last_seen_at"]) if "last_seen_at" in keys and row["last_seen_at"] else datetime.fromisoformat(row["fetched_at"]),
            last_verified_at=datetime.fromisoformat(row["last_verified_at"]) if "last_verified_at" in keys and row["last_verified_at"] else datetime.fromisoformat(row["fetched_at"]),
            status=row["status"] if "status" in keys else "ACTIVE",
            review_state=row["review_state"] if "review_state" in keys and row["review_state"] else "UNREVIEWED",
            applied_at=datetime.fromisoformat(row["applied_at"]) if "applied_at" in keys and row["applied_at"] else None,
        )

    # -------------------------------------------------------------------------
    # PIPELINE RUNS & DAILY MORNING GUARD METHODS
    # -------------------------------------------------------------------------

    def record_pipeline_run_start(
        self,
        run_type: str,
        is_daily_morning: bool,
        lagos_date: Optional[str] = None,
        started_at: Optional[str] = None,
    ) -> int:
        """Records the start of a pipeline run in pipeline_runs table and returns run_id."""
        if lagos_date is None:
            lagos_date = get_lagos_date_str()
        if started_at is None:
            started_at = datetime.now(timezone.utc).isoformat()

        query = """
        INSERT INTO pipeline_runs (
            run_type, status, lagos_date, started_at, is_daily_morning
        ) VALUES (?, 'STARTED', ?, ?, ?)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                query,
                (
                    run_type,
                    lagos_date,
                    started_at,
                    1 if is_daily_morning else 0,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def record_pipeline_run_complete(
        self,
        run_id: int,
        status: str,
        jobs_fetched: int = 0,
        jobs_new: int = 0,
        jobs_updated: int = 0,
        error_message: Optional[str] = None,
        completed_at: Optional[str] = None,
    ) -> None:
        """Updates a pipeline run record upon completion or failure."""
        if completed_at is None:
            completed_at = datetime.now(timezone.utc).isoformat()

        query = """
        UPDATE pipeline_runs
        SET status = ?,
            completed_at = ?,
            jobs_fetched = ?,
            jobs_new = ?,
            jobs_updated = ?,
            error_message = ?
        WHERE id = ?
        """
        with self.get_connection() as conn:
            conn.cursor().execute(
                query,
                (
                    status,
                    completed_at,
                    jobs_fetched,
                    jobs_new,
                    jobs_updated,
                    error_message,
                    run_id,
                ),
            )
            conn.commit()

    def is_morning_run_completed_for_date(self, lagos_date: str) -> bool:
        """Checks if a successful daily morning run (is_daily_morning=1) exists for given lagos_date."""
        query = """
        SELECT 1 FROM pipeline_runs
        WHERE lagos_date = ? AND is_daily_morning = 1 AND status = 'SUCCESS'
        LIMIT 1
        """
        with self.get_connection() as conn:
            row = conn.cursor().execute(query, (lagos_date,)).fetchone()
            return row is not None

    def get_morning_run_status(
        self, lagos_date: Optional[str] = None, now_dt: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Calculates morning run status for given date ('COMPLETED', 'FAILED', 'MISSED', 'NOT YET DUE')."""
        if now_dt is None:
            now_dt = get_local_now()
        if lagos_date is None:
            lagos_date = get_local_date_str(now_dt)

        query = """
        SELECT * FROM pipeline_runs
        WHERE lagos_date = ? AND is_daily_morning = 1
        ORDER BY id DESC
        """
        with self.get_connection() as conn:
            rows = [dict(r) for r in conn.cursor().execute(query, (lagos_date,)).fetchall()]

        success_row = next((r for r in rows if r["status"] == "SUCCESS"), None)
        failed_row = next((r for r in rows if r["status"] == "FAILED"), None)

        if success_row:
            state = "COMPLETED"
        elif failed_row and not success_row:
            state = "FAILED"
        else:
            if now_dt.hour >= 8:
                state = "MISSED"
            else:
                state = "NOT YET DUE"

        last_success = self.get_last_successful_run()
        last_attempt = self.get_last_attempt()

        return {
            "lagos_date": lagos_date,
            "status": state,
            "last_successful_run": last_success,
            "last_attempt": last_attempt,
            "today_attempts_count": len(rows),
        }

    def get_last_successful_run(self) -> Optional[Dict[str, Any]]:
        """Returns most recent pipeline run with status = 'SUCCESS'."""
        query = "SELECT * FROM pipeline_runs WHERE status = 'SUCCESS' ORDER BY id DESC LIMIT 1"
        with self.get_connection() as conn:
            row = conn.cursor().execute(query).fetchone()
            return dict(row) if row else None

    def get_last_attempt(self) -> Optional[Dict[str, Any]]:
        """Returns most recent pipeline run attempt."""
        query = "SELECT * FROM pipeline_runs ORDER BY id DESC LIMIT 1"
        with self.get_connection() as conn:
            row = conn.cursor().execute(query).fetchone()
            return dict(row) if row else None

    def get_recent_pipeline_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Returns list of recent pipeline runs."""
        query = "SELECT * FROM pipeline_runs ORDER BY id DESC LIMIT ?"
        with self.get_connection() as conn:
            rows = conn.cursor().execute(query, (limit,)).fetchall()
            return [dict(r) for r in rows]

