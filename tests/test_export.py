"""Unit and integration tests for Phase 9 — Excel Export Integration."""

import io
import os
import tempfile
import urllib.request
from datetime import datetime, timezone, timedelta
import openpyxl
import pytest

from job_monitor.db.storage import JobStorage
from job_monitor.models.normalized_job import NormalizedJob
from job_monitor.models.application import Application, ApplicationStatus, InterviewStage
from job_monitor.reports.excel_exporter import ExcelExporter
from job_monitor.dashboard.server import DashboardServer


@pytest.fixture
def temp_storage():
    """Provides a fresh temporary SQLite storage instance per test."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = tf.name

    storage = JobStorage(db_path=db_path)
    yield storage

    if os.path.exists(db_path):
        os.remove(db_path)


class TestExcelExporter:
    def test_export_zero_applications_structure(self, temp_storage):
        """Tests exporting when database has zero tracked applications (empty tracker)."""
        exporter = ExcelExporter(storage=temp_storage)
        excel_bytes = exporter.generate_workbook_bytes()
        assert len(excel_bytes) > 0

        # Load generated workbook with openpyxl
        wb = openpyxl.load_workbook(filename=io.BytesIO(excel_bytes))
        sheet_names = wb.sheetnames
        assert sheet_names == ["Applications", "Summary", "Daily Activity"]

        # 1. Applications Sheet
        ws_apps = wb["Applications"]
        headers = [cell.value for cell in ws_apps[1]]
        expected_headers = [
            "Job Title",
            "Company",
            "Source",
            "Job URL",
            "Date Discovered",
            "Date Applied",
            "Application Status",
            "Interview Stage",
            "Next Action",
            "Next Action Date",
            "Technical Score",
            "Priority Score",
            "Classification",
            "Location",
            "Remote Eligibility",
            "Notes",
            "Last Updated",
        ]
        assert headers == expected_headers
        assert ws_apps.max_row == 1  # Headers only, 0 data rows

        # 2. Summary Sheet
        ws_sum = wb["Summary"]
        assert ws_sum.max_row == 17  # Header + 16 metrics
        metrics = {ws_sum.cell(r, 1).value: ws_sum.cell(r, 2).value for r in range(2, ws_sum.max_row + 1)}
        assert metrics["Total Tracked Applications"] == "0"
        assert metrics["Applied Today"] == "0"
        assert metrics["Application-to-Interview Conversion Rate"] == "Historical transition data unavailable"

        # 3. Daily Activity Sheet
        ws_daily = wb["Daily Activity"]
        assert ws_daily.max_row == 31  # Header + 30 days
        daily_counts = [int(ws_daily.cell(r, 2).value) for r in range(2, ws_daily.max_row + 1)]
        assert len(daily_counts) == 30
        assert all(c == 0 for c in daily_counts)

    def test_export_single_application(self, temp_storage):
        """Tests exporting a single tracked application with full field mapping."""
        now = datetime.now(timezone.utc)
        j = NormalizedJob(
            id="job-exp-1",
            source_name="remotive",
            external_id="ext-exp-1",
            url="https://example.com/job/exp-1",
            title="Senior Python Engineer",
            company_name="Acme Corp",
            category="Backend / Software Engineering",
            location_requirement="Worldwide",
            is_remote=True,
            fetched_at=now,
        )
        temp_storage.save_normalized_job(j)

        app = Application(
            job_id=j.id,
            status=ApplicationStatus.APPLIED,
            applied_at=now,
            next_action="Follow up via email",
            next_action_date=now.strftime("%Y-%m-%d"),
            notes="Submitted via direct portal.",
        )
        temp_storage.create_application(app)

        exporter = ExcelExporter(storage=temp_storage)
        excel_bytes = exporter.generate_workbook_bytes()

        wb = openpyxl.load_workbook(filename=io.BytesIO(excel_bytes))
        ws_apps = wb["Applications"]
        assert ws_apps.max_row == 2  # Header + 1 data row

        row2 = [cell.value for cell in ws_apps[2]]
        assert row2[0] == "Senior Python Engineer"
        assert row2[1] == "Acme Corp"
        assert row2[2] == "remotive"
        assert row2[3] == "https://example.com/job/exp-1"
        assert row2[6] == "APPLIED"
        assert row2[8] == "Follow up via email"
        assert row2[15] == "Submitted via direct portal."

        # Check clickable hyperlink for Job URL
        url_cell = ws_apps.cell(row=2, column=4)
        assert url_cell.hyperlink is not None
        assert url_cell.hyperlink.target == "https://example.com/job/exp-1"

    def test_export_multiple_applications_and_formula_injection(self, temp_storage):
        """Tests exporting multiple applications, different statuses, missing fields, and formula injection protection."""
        now = datetime.now(timezone.utc)

        # Job with dangerous formula injection characters in title and company
        j1 = NormalizedJob(
            id="job-inj-1",
            source_name="jobicy",
            external_id="ext-inj-1",
            url="https://example.com/job/inj-1",
            title="=SUM(1,2) Developer",
            company_name="+CmdExec Corp",
            category="",
            fetched_at=now,
        )
        temp_storage.save_normalized_job(j1)

        app1 = Application(
            job_id=j1.id,
            status=ApplicationStatus.INTERVIEW,
            interview_stage=InterviewStage.STAGE_2,
            notes="-FormulaInNotes",
        )
        temp_storage.create_application(app1)

        j2 = NormalizedJob(
            id="job-inj-2",
            source_name="weworkremotely",
            external_id="ext-inj-2",
            url="https://example.com/job/inj-2",
            title="@Admin User Role",
            company_name="Safe Co",
            fetched_at=now,
        )
        temp_storage.save_normalized_job(j2)

        app2 = Application(
            job_id=j2.id,
            status=ApplicationStatus.OFFER,
        )
        temp_storage.create_application(app2)

        exporter = ExcelExporter(storage=temp_storage)
        excel_bytes = exporter.generate_workbook_bytes()

        wb = openpyxl.load_workbook(filename=io.BytesIO(excel_bytes))
        ws_apps = wb["Applications"]
        assert ws_apps.max_row == 3  # Header + 2 rows

        titles = [str(ws_apps.cell(r, 1).value or "") for r in (2, 3)]
        companies = [str(ws_apps.cell(r, 2).value or "") for r in (2, 3)]
        notes = [str(ws_apps.cell(r, 16).value or "") for r in (2, 3)]

        # Formula protection check: strings starting with =, +, -, @ must be prefixed with '
        assert any(t.startswith("'=SUM") for t in titles)
        assert any(c.startswith("'+CmdExec") for c in companies)
        assert any(t.startswith("'@Admin") for t in titles)
        assert any(n.startswith("'-FormulaInNotes") for n in notes)

    def test_no_database_mutations_during_export(self, temp_storage):
        """Verifies that exporting workbook does not mutate existing database records or counts."""
        j = NormalizedJob(
            id="job-mut-1",
            source_name="remotive",
            external_id="ext-mut-1",
            url="https://example.com/job/mut-1",
            title="Backend Engineer",
            company_name="Static Corp",
            fetched_at=datetime.now(timezone.utc),
        )
        temp_storage.save_normalized_job(j)

        app, _ = temp_storage.create_application(Application(job_id=j.id, status=ApplicationStatus.APPLIED))

        initial_count = temp_storage.count_applications_summary()["total_applications"]
        initial_app = temp_storage.get_application_by_id(app.id)

        exporter = ExcelExporter(storage=temp_storage)
        _ = exporter.generate_workbook_bytes()

        post_count = temp_storage.count_applications_summary()["total_applications"]
        post_app = temp_storage.get_application_by_id(app.id)

        assert initial_count == post_count
        assert initial_app.status == post_app.status
        assert initial_app.updated_at == post_app.updated_at


class TestExportRESTEndpoint:
    def test_excel_export_api_response_headers_and_payload(self, temp_storage):
        """Tests HTTP GET /api/export/applications.xlsx endpoint for status 200, valid XLSX headers, and filename."""
        server = DashboardServer(host="127.0.0.1", port=8597, db_path=temp_storage.db_path)
        server.start_background()

        try:
            url = "http://127.0.0.1:8597/api/export/applications.xlsx"
            req = urllib.request.urlopen(url)

            assert req.status == 200
            content_type = req.headers.get("Content-Type")
            content_disp = req.headers.get("Content-Disposition")

            assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in content_type
            assert "attachment; filename=\"Ann_Job_Applications_" in content_disp
            assert content_disp.endswith(".xlsx\"")

            body = req.read()
            assert len(body) > 0

            # Verify response is valid openpyxl workbook
            wb = openpyxl.load_workbook(filename=io.BytesIO(body))
            assert wb.sheetnames == ["Applications", "Summary", "Daily Activity"]

        finally:
            server.stop()
