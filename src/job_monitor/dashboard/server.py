import json
import socket
import sys
import threading
import time
import urllib.parse
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, Optional

from ..config import load_config
from ..db.storage import JobStorage
from ..reports.generator import DailyReportGenerator
from ..reports.excel_exporter import ExcelExporter
from ..scoring.eligibility import RemoteEligibility
from ..scoring.ranking import JobQueryService
from ..utils.logging import setup_logger
from .ui import get_dashboard_html

logger = setup_logger("dashboard.server")


class DashboardHTTPRequestHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler serving dashboard REST APIs and frontend single-page application."""

    # Injected dependencies shared across handler instances
    storage: Optional[JobStorage] = None
    query_service: Optional[JobQueryService] = None

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default stdout HTTP access logs unless debugging."""
        logger.debug(format, *args)

    def _send_json(self, data: Any, status_code: int = 200) -> None:
        """Helper to send JSON HTTP response."""
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html_str: str, status_code: int = 200) -> None:
        """Helper to send HTML HTTP response."""
        body = html_str.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, content_bytes: bytes, filename: str, content_type: str = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet") -> None:
        """Helper to send binary downloadable file HTTP response."""
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(content_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(content_bytes)

    def do_GET(self) -> None:
        """Handles HTTP GET requests."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path.rstrip("/")
        if not path:
            path = "/"

        query_params = urllib.parse.parse_qs(parsed_url.query)

        try:
            # Endpoint 1: Root SPA HTML
            if path == "/":
                cand_profile = None
                if self.query_service and self.query_service.scorer:
                    cand_profile = self.query_service.scorer.candidate_profile
                self._send_html(get_dashboard_html(candidate_profile=cand_profile))
                return

            # Endpoint 1.5: Pipeline Live Status
            if path == "/api/pipeline/status":
                from .status import PipelineStatusTracker
                self._send_json(PipelineStatusTracker.get_instance().to_dict())
                return


            # Endpoint 2: Summary Stats Cards
            if path == "/api/summary":
                storage = self.storage or JobStorage()
                query_svc = self.query_service or JobQueryService(storage=storage)

                all_scored = query_svc.evaluate_and_persist_matches()
                total_jobs = storage.count_jobs()
                nigeria_eligible = sum(1 for r in all_scored if r.explanation.remote_eligibility == RemoteEligibility.ELIGIBLE)
                strong_matches = sum(1 for r in all_scored if r.explanation.match_tier == "STRONG_MATCH" or r.explanation.priority_score >= 60.0)
                new_jobs = sum(1 for r in all_scored if r.explanation.freshness_factor >= 0.85)
                
                # Awaiting Application: Relevant active jobs without an application record and not dismissed
                apps_by_job_id = {app.job_id: app for app in storage.list_applications()}
                awaiting_app = sum(
                    1 for r in all_scored
                    if r.explanation.remote_eligibility == RemoteEligibility.ELIGIBLE
                    and r.explanation.priority_score > 0.0
                    and r.job.review_state != "DISMISSED"
                    and r.job.id not in apps_by_job_id
                )

                app_summary = storage.count_applications_summary()

                summary = {
                    "total_jobs": total_jobs,
                    "nigeria_eligible": nigeria_eligible,
                    "strong_matches": strong_matches,
                    "new_jobs": new_jobs,
                    "awaiting_application": awaiting_app,
                    "total_applications": app_summary["total_applications"],
                    "applications_this_week": app_summary["applications_this_week"],
                    "awaiting_response": app_summary["awaiting_response"],
                    "interviews": app_summary["interviews"],
                    "offers": app_summary["offers"],
                    "rejections": app_summary["rejections"],
                }
                self._send_json(summary)
                return

            # Endpoint 3: Main Dashboard Sections
            if path == "/api/dashboard":
                query_svc = self.query_service or JobQueryService(storage=self.storage or JobStorage())
                recs = query_svc.get_dashboard_recommendations(limit_per_section=10)

                data = {
                    "apply_first": [r.model_dump(mode="json") for r in recs["apply_first"]],
                    "fastest_cash": [r.model_dump(mode="json") for r in recs["fastest_cash"]],
                    "best_technical_match": [r.model_dump(mode="json") for r in recs["best_technical_match"]],
                    "best_long_term": [r.model_dump(mode="json") for r in recs["best_long_term"]],
                    "new_today": [r.model_dump(mode="json") for r in recs["new_today"]],
                }
                self._send_json(data)
                return


            # Endpoint 4: All Jobs List
            if path == "/api/jobs":
                query_svc = self.query_service or JobQueryService(storage=self.storage or JobStorage())
                all_scored = query_svc.evaluate_and_persist_matches()
                all_json = [r.model_dump(mode="json") for r in all_scored]
                self._send_json(all_json)
                return

            # Endpoint 5: Applications List (/api/applications)
            if path == "/api/applications":
                storage = self.storage or JobStorage()
                query_svc = self.query_service or JobQueryService(storage=storage)
                apps = storage.list_applications()
                all_scored = {r.job.id: r for r in query_svc.evaluate_and_persist_matches()}

                enriched_apps = []
                for app in apps:
                    app_dict = app.model_dump(mode="json")
                    scored_rec = all_scored.get(app.job_id)
                    if scored_rec:
                        app_dict["job"] = scored_rec.job.model_dump(mode="json")
                        app_dict["explanation"] = scored_rec.explanation.model_dump(mode="json")
                    else:
                        job_record = storage.get_job_by_id(app.job_id)
                        if job_record:
                            app_dict["job"] = job_record.model_dump(mode="json")
                    enriched_apps.append(app_dict)

                self._send_json(enriched_apps)
                return

            # Endpoint 6: Single Application Lookup (/api/applications/<app_id_or_job_id>)
            if path.startswith("/api/applications/"):
                ident = path.replace("/api/applications/", "").strip()
                storage = self.storage or JobStorage()
                query_svc = self.query_service or JobQueryService(storage=storage)

                app = storage.get_application_by_id(ident) or storage.get_application_by_job_id(ident)
                if app:
                    app_dict = app.model_dump(mode="json")
                    all_scored = {r.job.id: r for r in query_svc.evaluate_and_persist_matches()}
                    scored_rec = all_scored.get(app.job_id)
                    if scored_rec:
                        app_dict["job"] = scored_rec.job.model_dump(mode="json")
                        app_dict["explanation"] = scored_rec.explanation.model_dump(mode="json")
                    else:
                        job_record = storage.get_job_by_id(app.job_id)
                        if job_record:
                            app_dict["job"] = job_record.model_dump(mode="json")
                    self._send_json(app_dict)
                else:
                    self._send_json({"error": f"Application with ID '{ident}' not found."}, status_code=404)
                return

            # Endpoint 7: Single Job Details (/api/jobs/<job_id>)
            if path.startswith("/api/jobs/"):
                job_id = path.replace("/api/jobs/", "").strip()
                query_svc = self.query_service or JobQueryService(storage=self.storage or JobStorage())
                all_scored = query_svc.evaluate_and_persist_matches()

                found = next((r for r in all_scored if r.job.id == job_id), None)
                if found:
                    self._send_json(found.model_dump(mode="json"))
                else:
                    self._send_json({"error": f"Job with ID '{job_id}' not found."}, status_code=404)
                return

            # Endpoint 8: Latest Daily Report
            if path == "/api/reports/latest":
                query_svc = self.query_service or JobQueryService(storage=self.storage or JobStorage())
                generator = DailyReportGenerator(query_service=query_svc)
                report_markdown = generator.generate_report()
                self._send_json({"content": report_markdown})
                return

            # Endpoint 9: Analytics Endpoints
            if path == "/api/analytics/all":
                storage = self.storage or JobStorage()
                self._send_json(storage.get_full_analytics())
                return

            if path == "/api/analytics/summary":
                storage = self.storage or JobStorage()
                self._send_json(storage.get_analytics_summary())
                return

            if path == "/api/analytics/daily":
                storage = self.storage or JobStorage()
                days_param = 7
                if parsed_url.query:
                    qs = urllib.parse.parse_qs(parsed_url.query)
                    if "days" in qs and qs["days"][0].isdigit():
                        days_param = int(qs["days"][0])
                self._send_json(storage.get_daily_analytics(days=days_param))
                return

            if path == "/api/analytics/weekly":
                storage = self.storage or JobStorage()
                self._send_json(storage.get_weekly_summary())
                return

            if path == "/api/analytics/funnel":
                storage = self.storage or JobStorage()
                self._send_json(storage.get_funnel_analytics())
                return

            if path == "/api/analytics/sources":
                storage = self.storage or JobStorage()
                self._send_json(storage.get_source_analytics())
                return

            if path == "/api/analytics/categories":
                storage = self.storage or JobStorage()
                self._send_json(storage.get_category_analytics())
                return

            if path == "/api/analytics/next-actions":
                storage = self.storage or JobStorage()
                self._send_json(storage.get_next_actions_analytics())
                return

            # Endpoint 10: Excel Export Endpoint
            if path in ("/api/export/applications.xlsx", "/api/export/applications", "/api/analytics/export"):
                storage = self.storage or JobStorage()
                query_svc = self.query_service or JobQueryService(storage=storage)
                exporter = ExcelExporter(storage=storage, query_service=query_svc)
                excel_bytes = exporter.generate_workbook_bytes()
                today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                filename = f"Ann_Job_Applications_{today_str}.xlsx"
                self._send_file(excel_bytes, filename=filename)
                return

            # Fallback: 404 Not Found
            self._send_json({"error": "Endpoint not found"}, status_code=404)

        except Exception as e:
            logger.error("Error processing GET %s: %s", self.path, str(e), exc_info=True)
            self._send_json({"error": str(e)}, status_code=500)


    def do_POST(self) -> None:
        """Handles HTTP POST requests for state mutations (review state, application creation & updates)."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path.rstrip("/")

        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_length) if content_length > 0 else b"{}"
            payload = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}

            storage = self.storage or JobStorage()

            # Endpoint 0: Activation / Tab Focus Endpoint (/api/activate)
            if path == "/api/activate":
                client_ip = self.client_address[0]
                if client_ip not in ("127.0.0.1", "::1", "localhost"):
                    self._send_json({"error": "Forbidden: Loopback activation only"}, status_code=403)
                    return

                from ..utils.single_instance import focus_or_open_dashboard_tab
                url = get_runtime_dashboard_url()
                threading.Thread(target=lambda: focus_or_open_dashboard_tab(url), daemon=True).start()
                self._send_json({"success": True, "message": "Dashboard focused", "url": url})
                return

            # Endpoint 1: Update Review State (/api/jobs/<job_id>/review_state)
            if path.startswith("/api/jobs/") and path.endswith("/review_state"):
                parts = path.split("/")
                job_id = parts[3]
                review_state = payload.get("review_state", "UNREVIEWED").upper()

                if review_state not in ("UNREVIEWED", "REVIEWING", "DISMISSED"):
                    self._send_json({"error": "Invalid review_state"}, status_code=400)
                    return

                success = storage.update_review_state(job_id, review_state)
                if success:
                    self._send_json({"success": True, "job_id": job_id, "review_state": review_state})
                else:
                    self._send_json({"error": f"Job ID '{job_id}' not found."}, status_code=404)
                return

            # Endpoint 2: Mark as Applied Intent (/api/jobs/<job_id>/apply_intent)
            if path.startswith("/api/jobs/") and path.endswith("/apply_intent"):
                parts = path.split("/")
                job_id = parts[3]
                
                success = storage.mark_as_applied(job_id)
                if success:
                    updated_job = storage.get_job_by_id(job_id)
                    app = storage.get_application_by_job_id(job_id)
                    applied_at_str = updated_job.applied_at.isoformat() if updated_job and updated_job.applied_at else None
                    self._send_json({
                        "success": True,
                        "job_id": job_id,
                        "applied_at": applied_at_str,
                        "application": app.model_dump(mode="json") if app else None
                    })
                else:
                    self._send_json({"error": f"Job ID '{job_id}' not found."}, status_code=404)
                return

            # Endpoint 3: Create Application (/api/applications)
            if path == "/api/applications":
                job_id = payload.get("job_id")
                if not job_id:
                    self._send_json({"error": "Missing job_id"}, status_code=400)
                    return

                status_str = payload.get("status", "APPLIED").upper()
                stage_str = payload.get("interview_stage", "NONE").upper()
                
                from ..models.application import Application, ApplicationStatus, InterviewStage
                app = Application(
                    job_id=job_id,
                    status=ApplicationStatus(status_str) if status_str in ApplicationStatus.__members__ else ApplicationStatus.APPLIED,
                    interview_stage=InterviewStage(stage_str) if stage_str in InterviewStage.__members__ else InterviewStage.NONE,
                    next_action=payload.get("next_action"),
                    next_action_date=payload.get("next_action_date"),
                    notes=payload.get("notes"),
                )

                created, is_new = storage.create_application(app)
                self._send_json({"success": True, "created": is_new, "application": created.model_dump(mode="json")})
                return

            # Endpoint 4: Update Application (/api/applications/<app_id>)
            if path.startswith("/api/applications/"):
                app_id = path.replace("/api/applications/", "").strip()
                from ..models.application import ApplicationStatus, InterviewStage
                
                status_enum = ApplicationStatus(payload["status"].upper()) if "status" in payload and payload["status"].upper() in ApplicationStatus.__members__ else None
                stage_enum = InterviewStage(payload["interview_stage"].upper()) if "interview_stage" in payload and payload["interview_stage"].upper() in InterviewStage.__members__ else None

                updated = storage.update_application(
                    app_id=app_id,
                    status=status_enum,
                    interview_stage=stage_enum,
                    next_action=payload.get("next_action"),
                    next_action_date=payload.get("next_action_date"),
                    notes=payload.get("notes"),
                )

                if updated:
                    self._send_json({"success": True, "application": updated.model_dump(mode="json")})
                else:
                    self._send_json({"error": f"Application with ID '{app_id}' not found."}, status_code=404)
                return

            self._send_json({"error": "Endpoint not found"}, status_code=404)

        except Exception as e:
            logger.error("Error processing POST %s: %s", self.path, str(e), exc_info=True)
            self._send_json({"error": str(e)}, status_code=500)




_RUNTIME_DASHBOARD_URL: str = "http://127.0.0.1:8500"


def get_runtime_dashboard_url() -> str:
    """Returns currently active runtime dashboard URL."""
    return _RUNTIME_DASHBOARD_URL


def set_runtime_dashboard_url(url: str) -> None:
    """Sets currently active runtime dashboard URL."""
    global _RUNTIME_DASHBOARD_URL
    _RUNTIME_DASHBOARD_URL = url


from ..scoring.candidate_profile import load_candidate_profile
from ..scoring.scorer import JobScorer


class AppHTTPServer(HTTPServer):
    """HTTPServer with platform-aware socket reuse configuration.

    On Windows (win32), setting SO_REUSEADDR=1 allows socket hijacking and multiple
    listeners on the same port. Disabling allow_reuse_address on Windows ensures that
    attempting to bind to an occupied port correctly raises WSAEADDRINUSE (errno 10048).
    """
    allow_reuse_address = sys.platform != "win32"


class DashboardServer:
    """Server runner encapsulating HTTP server lifecycle with dynamic port fallback."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8500, db_path: Optional[str] = None, profile_name: Optional[str] = None):
        self.host = host
        self.port = port
        self.config = load_config(profile_name=profile_name)
        self.candidate_profile = load_candidate_profile(self.config.active_profile)
        self.db_path = db_path or self.config.database.path
        self.storage = JobStorage(db_path=self.db_path)
        self.scorer = JobScorer(candidate_profile=self.candidate_profile)
        self.query_service = JobQueryService(storage=self.storage, scorer=self.scorer)
        self.httpd: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None

    def _bind_server(self) -> HTTPServer:
        """Binds HTTPServer attempting preferred port first, falling back to next ports if unavailable."""
        current_port = self.port
        max_attempts = 50
        for attempt in range(max_attempts):
            try:
                server_address = (self.host, current_port)
                httpd = AppHTTPServer(server_address, DashboardHTTPRequestHandler)
                if current_port != self.port:
                    logger.warning("Preferred port %d unavailable. Bound to fallback port %d.", self.port, current_port)
                self.port = current_port
                self.config.dashboard.port = current_port
                active_url = f"http://{self.host}:{self.port}"
                set_runtime_dashboard_url(active_url)
                from ..utils.single_instance import SingleInstanceManager
                SingleInstanceManager.register_instance(current_port, profile_name=self.config.active_profile)
                return httpd
            except OSError as e:
                err_msg = str(e)
                if "Address already in use" in err_msg or getattr(e, "errno", None) in (48, 98, 10048):
                    current_port += 1
                else:
                    raise e
        raise OSError(f"Could not bind dashboard server to any port in range {self.port}-{current_port}")

    def start_background(self) -> None:
        """Starts HTTP server in a background thread."""
        DashboardHTTPRequestHandler.storage = self.storage
        DashboardHTTPRequestHandler.query_service = self.query_service

        self.httpd = self._bind_server()
        logger.info("Dashboard HTTP server running on http://%s:%d", self.host, self.port)

        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        """Stops background HTTP server cleanly."""
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            from ..utils.single_instance import SingleInstanceManager
            SingleInstanceManager.cleanup_metadata()
            logger.info("Dashboard HTTP server shut down successfully.")

    def run_forever(self, open_browser: bool = True) -> None:
        """Starts HTTP server synchronously and blocks until interrupted."""
        DashboardHTTPRequestHandler.storage = self.storage
        DashboardHTTPRequestHandler.query_service = self.query_service

        if not self.httpd:
            self.httpd = self._bind_server()


        url = f"http://{self.host}:{self.port}"
        print("=" * 60)
        print("  ANN'S JOB INTELLIGENCE DASHBOARD")
        print("=" * 60)
        print(f"  Status:  ACTIVE")
        print(f"  Profile: {self.candidate_profile.name} ({self.candidate_profile.id})")
        print(f"  URL:     {url}")
        print(f"  Database: {self.storage.db_path}")
        print("  Press Ctrl+C to stop the dashboard server.")
        print("=" * 60)

        if open_browser:
            threading.Thread(target=self._launch_browser_delayed, args=(url,), daemon=True).start()

        try:
            self.httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down dashboard server...")
            self.stop()

    def _launch_browser_delayed(self, url: str) -> None:
        """Launches web browser after slight delay to ensure server is ready."""
        time.sleep(0.5)
        webbrowser.open(url)


def run_dashboard_server(host: str = "127.0.0.1", port: int = 8500, open_browser: bool = True, db_path: Optional[str] = None, profile_name: Optional[str] = None) -> None:
    """Utility function to launch dashboard server."""
    server = DashboardServer(host=host, port=port, db_path=db_path, profile_name=profile_name)
    server.run_forever(open_browser=open_browser)

