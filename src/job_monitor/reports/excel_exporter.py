"""Excel Workbook Exporter Service for Ann's Job Intelligence & Application Tracker."""

import io
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from ..db.storage import JobStorage
from ..scoring.ranking import JobQueryService, ScoredJobRecord
from ..utils.logging import setup_logger

logger = setup_logger("reports.excel_exporter")



class ExcelExporter:
    """Generates downloadable formatted Excel workbook (XLSX) from SQLite storage."""

    def __init__(self, storage: JobStorage, query_service: Optional[JobQueryService] = None):
        self.storage = storage
        self.query_service = query_service or JobQueryService(storage=storage)

    def generate_workbook_bytes(self) -> bytes:
        """Creates complete in-memory Excel workbook and returns raw binary bytes."""
        try:
            import openpyxl
        except ImportError as err:
            raise RuntimeError("openpyxl package is required for Excel exporting") from err

        wb = openpyxl.Workbook()
        # Remove default sheet
        wb.remove(wb.active)


        # Fetch data
        apps = self.storage.list_applications()
        analytics = self.storage.get_full_analytics()

        # Build scored jobs map for technical scores and explanations
        scored_map: Dict[str, ScoredJobRecord] = {}
        try:
            scored_records = self.query_service.evaluate_and_persist_matches()
            scored_map = {r.job.id: r for r in scored_records}
        except Exception as e:
            logger.warning("Could not evaluate job scores for export: %s", str(e))

        # 1. Build Applications Sheet
        self._build_applications_sheet(wb, apps, scored_map)

        # 2. Build Summary Sheet
        self._build_summary_sheet(wb, analytics)

        # 3. Build Daily Activity Sheet
        self._build_daily_activity_sheet(wb, analytics)

        # Save to binary stream
        stream = io.BytesIO()
        wb.save(stream)
        stream.seek(0)
        return stream.getvalue()

    def _build_applications_sheet(self, wb: Any, apps: List[Any], scored_map: Dict[str, ScoredJobRecord]) -> None:
        """Constructs Worksheet 1: Applications with 17 required columns."""
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

        ws = wb.create_sheet(title="Applications")

        headers = [
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

        ws.append(headers)

        # Styling definitions
        header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

        data_font = Font(name="Arial", size=9)
        link_font = Font(name="Arial", size=9, color="2563EB", underline="single")
        left_align = Alignment(horizontal="left", vertical="top")
        wrap_align = Alignment(horizontal="left", vertical="top", wrap_text=True)
        center_align = Alignment(horizontal="center", vertical="top")

        thin_border = Border(
            left=Side(style="thin", color="E2E8F0"),
            right=Side(style="thin", color="E2E8F0"),
            top=Side(style="thin", color="E2E8F0"),
            bottom=Side(style="thin", color="E2E8F0"),
        )

        # Style header row
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align
            cell.border = thin_border
        ws.row_dimensions[1].height = 28

        # Populate rows
        for row_idx, app in enumerate(apps, start=2):
            job_record = None
            scored_rec = scored_map.get(app.job_id)
            if scored_rec:
                job_record = scored_rec.job
                explanation = scored_rec.explanation
            else:
                job_record = self.storage.get_job_by_id(app.job_id)
                explanation = None

            # Job details
            job_title = job_record.title if job_record else "Unknown Title"
            company = job_record.company_name if job_record else "Unknown Company"
            source = job_record.source_name if job_record else "Unknown"
            job_url = job_record.url if job_record else ""
            date_disc = job_record.first_seen_at.strftime("%Y-%m-%d") if (job_record and job_record.first_seen_at) else ""
            location = job_record.location_requirement if (job_record and job_record.location_requirement) else "Anywhere / Worldwide"

            # Application details
            date_applied = app.applied_at.strftime("%Y-%m-%d") if app.applied_at else ""
            app_status = app.status.value if hasattr(app.status, "value") else str(app.status)
            interview_stage = app.interview_stage.value if hasattr(app.interview_stage, "value") else str(app.interview_stage)
            next_action = app.next_action or ""
            next_action_date = app.next_action_date or ""
            notes = app.notes or ""
            last_updated = app.updated_at.strftime("%Y-%m-%d %H:%M") if app.updated_at else ""

            # Scores & classification
            tech_score = f"{explanation.technical_match_score:.1f}" if explanation else "N/A"
            prio_score = f"{explanation.priority_score:.1f}" if explanation else "N/A"
            classification = (
                explanation.role_relevance.value
                if (explanation and hasattr(explanation.role_relevance, "value"))
                else (job_record.category if (job_record and job_record.category) else "Software Engineering")
            )
            remote_elig = (
                explanation.remote_eligibility.value
                if (explanation and hasattr(explanation.remote_eligibility, "value"))
                else ("ELIGIBLE" if (job_record and job_record.is_remote) else "UNCERTAIN")
            )

            row_values = [
                self._sanitize(job_title),
                self._sanitize(company),
                self._sanitize(source),
                job_url,
                date_disc,
                date_applied,
                app_status,
                interview_stage,
                self._sanitize(next_action),
                next_action_date,
                tech_score,
                prio_score,
                self._sanitize(classification),
                self._sanitize(location),
                remote_elig,
                self._sanitize(notes),
                last_updated,
            ]

            for col_idx, val in enumerate(row_values, start=1):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.border = thin_border
                cell.font = data_font

                if col_idx == 4 and val:  # Job URL Hyperlink
                    cell.value = str(val)
                    cell.hyperlink = str(val)
                    cell.font = link_font
                    cell.alignment = left_align
                elif col_idx in (5, 6, 7, 8, 10, 11, 12, 14, 15, 17):
                    cell.value = str(val)
                    cell.alignment = center_align
                else:
                    cell.value = str(val)
                    cell.alignment = wrap_align

        ws.freeze_panes = "A2"
        if len(apps) > 0:
            ws.auto_filter.ref = ws.dimensions

        self._auto_fit_columns(ws, min_width=12, max_width=45)

    def _build_summary_sheet(self, wb: Any, analytics: Dict[str, Any]) -> None:
        """Constructs Worksheet 2: Summary with top metrics and historical conversion rates."""
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

        ws = wb.create_sheet(title="Summary")

        export_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        summary = analytics.get("summary", {})
        funnel = analytics.get("funnel", {})
        formatted_rates = funnel.get("formatted_rates", {})

        metrics_data = [
            ("Export Date", export_date),
            ("Total Tracked Applications", summary.get("total_applications", 0)),
            ("Applied Today", summary.get("applications_today", 0)),
            ("Applied Yesterday", summary.get("applications_yesterday", 0)),
            ("Applied in Last 7 Days", summary.get("applications_7_days", 0)),
            ("Applied in Last 30 Days", summary.get("applications_30_days", 0)),
            ("Awaiting Response", summary.get("awaiting_response", 0)),
            ("Assessments", summary.get("assessments", 0)),
            ("Interviews", summary.get("interviews", 0)),
            ("Offers", summary.get("offers", 0)),
            ("Accepted", summary.get("accepted", 0)),
            ("Rejected", summary.get("rejections", 0)),
            ("Withdrawn", summary.get("withdrawn", 0)),
            ("Application-to-Interview Conversion Rate", formatted_rates.get("app_to_interview", "N/A")),
            ("Application-to-Offer Conversion Rate", formatted_rates.get("app_to_offer", "N/A")),
            ("Interview-to-Offer Conversion Rate", formatted_rates.get("interview_to_offer", "N/A")),
        ]

        # Header
        ws.append(["Metric", "Value"])

        header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        header_align = Alignment(horizontal="center", vertical="center")

        data_font = Font(name="Arial", size=10)
        label_font = Font(name="Arial", size=10, bold=True)
        thin_border = Border(
            left=Side(style="thin", color="E2E8F0"),
            right=Side(style="thin", color="E2E8F0"),
            top=Side(style="thin", color="E2E8F0"),
            bottom=Side(style="thin", color="E2E8F0"),
        )

        for col_idx in (1, 2):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align
            cell.border = thin_border
        ws.row_dimensions[1].height = 26

        for row_idx, (metric, val) in enumerate(metrics_data, start=2):
            c1 = ws.cell(row=row_idx, column=1, value=metric)
            c2 = ws.cell(row=row_idx, column=2, value=str(val))

            c1.font = label_font
            c1.border = thin_border
            c1.alignment = Alignment(horizontal="left", vertical="center")

            c2.font = data_font
            c2.border = thin_border
            c2.alignment = Alignment(horizontal="center", vertical="center")

        ws.freeze_panes = "A2"
        self._auto_fit_columns(ws, min_width=25, max_width=60)

    def _build_daily_activity_sheet(self, wb: Any, analytics: Dict[str, Any]) -> None:
        """Constructs Worksheet 3: Daily Activity covering the last 30 calendar days."""
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

        ws = wb.create_sheet(title="Daily Activity")

        ws.append(["Date", "Applications Submitted"])

        header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        header_align = Alignment(horizontal="center", vertical="center")

        data_font = Font(name="Arial", size=9)
        thin_border = Border(
            left=Side(style="thin", color="E2E8F0"),
            right=Side(style="thin", color="E2E8F0"),
            top=Side(style="thin", color="E2E8F0"),
            bottom=Side(style="thin", color="E2E8F0"),
        )

        for col_idx in (1, 2):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align
            cell.border = thin_border
        ws.row_dimensions[1].height = 26

        daily_30 = analytics.get("daily_activity_30d", [])
        if not daily_30:
            daily_30 = self.storage.get_daily_analytics(days=30)

        for row_idx, item in enumerate(daily_30, start=2):
            c1 = ws.cell(row=row_idx, column=1, value=item["date"])
            c2 = ws.cell(row=row_idx, column=2, value=int(item["count"]))

            c1.font = data_font
            c1.border = thin_border
            c1.alignment = Alignment(horizontal="center", vertical="center")

            c2.font = data_font
            c2.border = thin_border
            c2.alignment = Alignment(horizontal="center", vertical="center")

        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        self._auto_fit_columns(ws, min_width=18, max_width=35)

    def _sanitize(self, val: Any) -> str:
        """Sanitizes text value against spreadsheet formula injection (=, +, -, @)."""
        if val is None:
            return ""
        s = str(val)
        stripped = s.lstrip()
        if stripped and stripped[0] in ("=", "+", "-", "@"):
            return f"'{s}"
        return s

    def _auto_fit_columns(self, ws: Any, min_width: int = 12, max_width: int = 50) -> None:
        """Calculates optimal column width based on content length."""
        from openpyxl.utils import get_column_letter

        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or "")
                if "\n" in val_str:
                    val_str = max(val_str.split("\n"), key=len)
                max_len = max(max_len, len(val_str))
            ws.column_dimensions[col_letter].width = min(max(max_len + 4, min_width), max_width)

