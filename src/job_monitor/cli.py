import argparse
import sys
import threading
import webbrowser
from typing import List
from .dashboard.server import DashboardServer, run_dashboard_server
from .notifications.desktop_macos import MacOSDesktopNotifier
from .pipeline_runner import OperationalPipelineRunner
from .utils.logging import setup_logger
from .utils.single_instance import SingleInstanceManager, focus_or_open_dashboard_tab

logger = setup_logger("cli")


def main(argv: List[str] = None) -> None:
    parser = argparse.ArgumentParser(
        prog="job-monitor",
        description="Personal Remote Job Intelligence & Cashflow Monitoring System CLI",
    )
    parser.add_argument("--profile", type=str, default=None, help="Candidate profile name or path (e.g. 'example')")
    subparsers = parser.add_subparsers(dest="command", help="Operational commands")

    # Command: run
    run_parser = subparsers.add_parser("run", help="Execute full ingestion, evaluation, reporting, and notification cycle")
    run_parser.add_argument("--limit", type=int, default=None, help="Optional job limit per source (for quick testing)")
    run_parser.add_argument("--scheduled", action="store_true", help="Execute as daily scheduled morning run with missed-run recovery check")
    run_parser.add_argument("--force", action="store_true", help="Force execution even if scheduled run already completed today")
    run_parser.add_argument("--profile", type=str, default=None, help="Candidate profile name or path")

    # Command: report
    report_parser = subparsers.add_parser("report", help="Generate daily report from existing database without re-fetching")
    report_parser.add_argument("--profile", type=str, default=None, help="Candidate profile name or path")

    # Command: status
    status_parser = subparsers.add_parser("status", help="Display system, database, ingestion, and morning run status")
    status_parser.add_argument("--profile", type=str, default=None, help="Candidate profile name or path")

    # Command: dashboard
    dash_parser = subparsers.add_parser("dashboard", help="Start local web dashboard server")
    dash_parser.add_argument("--port", type=int, default=8500, help="Port to run dashboard server on (default: 8500)")
    dash_parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1)")
    dash_parser.add_argument("--no-browser", action="store_true", help="Do not automatically open browser on startup")
    dash_parser.add_argument("--profile", type=str, default=None, help="Candidate profile name or path")

    # Command: test-notification
    subparsers.add_parser("test-notification", help="Send a test macOS desktop notification")

    args = parser.parse_args(argv)
    profile_name = getattr(args, "profile", None)

    if not args.command:
        # Desktop Application Mode (launched via Finder / double-click with no CLI args)
        import time
        from .dashboard.server import get_runtime_dashboard_url
        from .utils.single_instance import SingleInstanceManager, focus_or_open_dashboard_tab

        # Resolve active candidate profile name dynamically
        from .config import load_config
        active_config = load_config(profile_name=profile_name)
        active_profile = active_config.active_profile

        # Pre-Flight Single Instance Verification with Profile Isolation
        active_meta = SingleInstanceManager.is_instance_active(profile_name=active_profile)
        if active_meta:
            logger.info("Active instance detected for profile '%s' on port %s (PID %s). Activating dashboard browser...", active_profile, active_meta.get("port"), active_meta.get("pid"))
            SingleInstanceManager.activate_instance(active_meta)
            return

        server = DashboardServer(profile_name=profile_name)
        server.httpd = server._bind_server()
        active_url = get_runtime_dashboard_url()

        def _run_background_pipeline():
            try:
                runner = OperationalPipelineRunner(profile_name=profile_name)
                runner.run_full_cycle()
            except Exception as e:
                logger.error("Error executing background job pipeline: %s", str(e))

        bg_thread = threading.Thread(target=_run_background_pipeline, daemon=True)
        bg_thread.start()

        # Automatically open or focus browser to live bound dashboard URL
        threading.Thread(target=lambda: (time.sleep(0.5), focus_or_open_dashboard_tab(active_url)), daemon=True).start()

        server.run_forever(open_browser=False)


    elif args.command == "run":
        runner = OperationalPipelineRunner(profile_name=profile_name)
        report_text = runner.run_full_cycle(
            limit_per_source=getattr(args, "limit", None),
            is_scheduled=getattr(args, "scheduled", False),
            force=getattr(args, "force", False),
        )
        if report_text:
            print("\n" + report_text)


    elif args.command == "report":
        runner = OperationalPipelineRunner(profile_name=profile_name)
        report_text = runner.generate_report_only()
        print("\n" + report_text)

    elif args.command == "status":
        runner = OperationalPipelineRunner(profile_name=profile_name)
        count = runner.storage.count_jobs()
        morning_status = runner.storage.get_morning_run_status()
        recent_runs = runner.storage.get_recent_pipeline_runs(limit=5)

        print("=" * 60)
        print("  JOB MONITOR SYSTEM STATUS")
        print("=" * 60)
        print(f"Profile Name:         {runner.candidate_profile.name} ({runner.candidate_profile.id})")
        print(f"Database Path:        {runner.storage.db_path}")
        print(f"Total Stored Jobs:    {count}")
        print(f"Lagos Date Today:     {morning_status['lagos_date']}")
        print(f"Morning Run Status:   {morning_status['status']}")

        last_succ = morning_status["last_successful_run"]
        if last_succ:
            print(f"Last Successful Run:  {last_succ['completed_at'] or last_succ['started_at']} ({last_succ['run_type']})")
        else:
            print("Last Successful Run:  No successful run recorded.")

        last_att = morning_status["last_attempt"]
        if last_att:
            print(f"Last Attempt:         {last_att['started_at']} ({last_att['status']})")

        if recent_runs:
            print("-" * 60)
            print("Recent Pipeline Runs:")
            for r in recent_runs:
                flag = " [MORNING]" if r.get("is_daily_morning") else ""
                print(f"  #{r['id']} | {r['lagos_date']} | {r['run_type']:<9} | {r['status']:<7} | Fetched: {r['jobs_fetched']} | New: {r['jobs_new']}{flag}")
        print("=" * 60)

    elif args.command == "dashboard":
        run_dashboard_server(
            host=args.host,
            port=args.port,
            open_browser=not args.no_browser,
            profile_name=profile_name,
        )

    elif args.command == "test-notification":
        notifier = MacOSDesktopNotifier()
        success = notifier.send_notification(
            title="Job Monitor Test",
            message="7 new relevant jobs today — 3 strong backend matches!",
            subtitle="Desktop Notification Working",
        )
        if success:
            print("SUCCESS: Test desktop notification sent.")
        else:
            print("FAILURE: Could not send desktop notification.")


if __name__ == "__main__":
    main()
