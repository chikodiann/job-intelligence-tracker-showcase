import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from ..db.storage import JobStorage
from ..utils.logging import setup_logger

logger = setup_logger("reports.history")

CREATE_REPORT_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS report_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_timestamp TEXT NOT NULL,
    source_status_json TEXT NOT NULL,
    jobs_fetched INTEGER NOT NULL,
    jobs_new INTEGER NOT NULL,
    jobs_updated INTEGER NOT NULL,
    jobs_closed INTEGER NOT NULL,
    top_ranked_job_ids_json TEXT NOT NULL,
    report_markdown TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


class ReportHistoryStore:
    """Persists and retrieves daily report execution metadata and history."""

    def __init__(self, storage: JobStorage, output_dir: Optional[str] = None):
        if output_dir is None or output_dir == "data/reports":
            from ..utils.paths import AppPaths
            output_dir = str(AppPaths.get_reports_dir())
        self.storage = storage
        self.output_dir = output_dir
        self._ensure_table()

    def _ensure_table(self) -> None:
        """Initializes report_history table."""
        with self.storage.get_connection() as conn:
            conn.cursor().execute(CREATE_REPORT_HISTORY_TABLE)
            conn.commit()

    def save_report_run(
        self,
        source_status: Dict[str, Any],
        jobs_fetched: int,
        jobs_new: int,
        jobs_updated: int,
        jobs_closed: int,
        top_job_ids: List[str],
        report_markdown: str,
        output_dir: Optional[str] = None,
    ) -> int:
        """Saves report run to database and writes markdown file to output directory."""
        now = datetime.now(timezone.utc)
        iso_str = now.isoformat()

        # Write markdown file
        target_dir = Path(output_dir or self.output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / f"report_{now.strftime('%Y_%m_%d_%H%M%S')}.md"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(report_markdown)

        # Save record in SQLite
        query = """
        INSERT INTO report_history (
            run_timestamp, source_status_json, jobs_fetched, jobs_new,
            jobs_updated, jobs_closed, top_ranked_job_ids_json, report_markdown
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                query,
                (
                    iso_str,
                    json.dumps(source_status),
                    jobs_fetched,
                    jobs_new,
                    jobs_updated,
                    jobs_closed,
                    json.dumps(top_job_ids),
                    report_markdown,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_latest_report(self) -> Optional[Dict[str, Any]]:
        """Retrieves most recent report run from database."""
        query = "SELECT * FROM report_history ORDER BY id DESC LIMIT 1"
        with self.storage.get_connection() as conn:
            row = conn.cursor().execute(query).fetchone()
            if not row:
                return None
            return {
                "id": row["id"],
                "run_timestamp": row["run_timestamp"],
                "source_status": json.loads(row["source_status_json"]),
                "jobs_fetched": row["jobs_fetched"],
                "jobs_new": row["jobs_new"],
                "jobs_updated": row["jobs_updated"],
                "jobs_closed": row["jobs_closed"],
                "top_job_ids": json.loads(row["top_ranked_job_ids_json"]),
                "report_markdown": row["report_markdown"],
            }
