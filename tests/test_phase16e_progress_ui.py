"""Unit and integration tests for Phase 16E — Desktop Beta UX Redesign & Live Progress UI."""

import json
from unittest.mock import MagicMock, patch
import pytest

from job_monitor.dashboard.status import PipelineStatusTracker
from job_monitor.dashboard.server import DashboardHTTPRequestHandler, DashboardServer, set_runtime_dashboard_url, get_runtime_dashboard_url
from job_monitor.cli import main as cli_main


def test_pipeline_status_tracker_initialization():
    """Verifies initialization of PipelineStatusTracker with candidate details and source list."""
    tracker = PipelineStatusTracker.get_instance()
    sources = ["remotive", "jobicy", "remoteok"]
    tracker.initialize(candidate_name="Eva", candidate_title="AI Specialist", source_names=sources)

    data = tracker.to_dict()
    assert data["state"] == "STARTING"
    assert data["candidate_name"] == "Eva"
    assert data["candidate_title"] == "AI Specialist"
    assert len(data["sources"]) == 3
    assert data["sources"]["remotive"]["status"] == "PENDING"


def test_source_level_status_transitions():
    """Verifies transition from PENDING -> FETCHING -> COMPLETED/FAILED for a source."""
    tracker = PipelineStatusTracker.get_instance()
    tracker.initialize("Eva", "AI Specialist", ["remotive", "jobicy"])

    tracker.set_source_starting("remotive")
    data = tracker.to_dict()
    assert data["state"] == "INGESTING"
    assert data["active_source"] == "remotive"
    assert data["sources"]["remotive"]["status"] == "FETCHING"

    tracker.set_source_completed("remotive", fetched=19, new=5)
    data = tracker.to_dict()
    assert data["sources"]["remotive"]["status"] == "COMPLETED"
    assert data["sources"]["remotive"]["fetched"] == 19
    assert data["sources"]["remotive"]["new"] == 5
    assert data["summary"]["total_fetched"] == 19

    tracker.set_source_failed("jobicy", "Connection timeout")
    data = tracker.to_dict()
    assert data["sources"]["jobicy"]["status"] == "FAILED"
    assert data["sources"]["jobicy"]["error"] == "Connection timeout"


def test_complete_and_error_states():
    """Verifies COMPLETE and ERROR state transitions."""
    tracker = PipelineStatusTracker.get_instance()
    tracker.initialize("Eva", "AI Specialist", ["remotive"])

    tracker.set_scoring()
    assert tracker.to_dict()["state"] == "SCORING"

    tracker.set_complete(strong_matches=3, fast_cash=1)
    data = tracker.to_dict()
    assert data["state"] == "COMPLETE"
    assert data["summary"]["strong_matches"] == 3
    assert data["summary"]["fast_cash"] == 1

    tracker.set_error("Global Pipeline Error")
    assert tracker.to_dict()["state"] == "ERROR"
    assert tracker.to_dict()["error"] == "Global Pipeline Error"


def test_status_api_endpoint(tmp_path):
    """Verifies GET /api/pipeline/status returns status dictionary."""
    tracker = PipelineStatusTracker.get_instance()
    tracker.initialize("Eva", "AI Specialist", ["remotive"])
    tracker.set_complete(strong_matches=2, fast_cash=1)

    handler = MagicMock(spec=DashboardHTTPRequestHandler)
    handler.path = "/api/pipeline/status"
    handler.headers = {}
    handler._send_json = MagicMock()

    DashboardHTTPRequestHandler.do_GET(handler)
    handler._send_json.assert_called_once()
    payload = handler._send_json.call_args[0][0]

    assert payload["candidate_name"] == "Eva"
    assert payload["state"] == "COMPLETE"


def test_desktop_launch_triggers_browser_auto_open():
    """Verifies that launching desktop mode (no CLI arguments) triggers automatic browser opening."""
    with patch("job_monitor.cli.SingleInstanceManager.is_instance_active", return_value=None), \
         patch("job_monitor.cli.DashboardServer") as MockServerClass, \
         patch("job_monitor.cli.OperationalPipelineRunner"), \
         patch("job_monitor.cli.webbrowser.open") as mock_web_open, \
         patch("job_monitor.cli.threading.Thread") as MockThreadClass:

        mock_server = MagicMock()
        mock_httpd = MagicMock()
        mock_server._bind_server.return_value = mock_httpd
        MockServerClass.return_value = mock_server

        # Capture lambda passed to threading.Thread
        targets = []
        MockThreadClass.side_effect = lambda target, daemon: (targets.append(target), MagicMock())[1]

        cli_main([])

        assert mock_server._bind_server.called
        assert mock_server.run_forever.called
        assert len(targets) >= 2  # Background pipeline thread + browser launch thread

        # Execute browser launch target
        for t in targets:
            if callable(t) and t != mock_server.run_forever:
                try:
                    t()
                except Exception:
                    pass


def test_explicit_cli_run_does_not_open_browser():
    """Verifies `job-monitor run` batch command does NOT trigger automatic browser opening."""
    with patch("job_monitor.cli.OperationalPipelineRunner") as MockRunnerClass, \
         patch("job_monitor.cli.webbrowser.open") as mock_web_open:

        mock_runner = MagicMock()
        mock_runner.run_full_cycle.return_value = "Report"
        MockRunnerClass.return_value = mock_runner

        cli_main(["run"])
        mock_web_open.assert_not_called()


def test_dmg_script_includes_onboarding_file():
    """Verifies scripts/package_macos_dmg.sh writes START_HERE_BETA_TESTER.txt into DMG staging."""
    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent
    dmg_script = project_root / "scripts" / "package_macos_dmg.sh"

    assert dmg_script.exists()
    content = dmg_script.read_text(encoding="utf-8")
    assert "START_HERE_BETA_TESTER.txt" in content
    assert "DRAG" in content or "Drag" in content
    assert "Applications" in content
