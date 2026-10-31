"""Unit and integration tests for Phase 10 — macOS Notification & Dashboard Integration."""

import os
import sys
import tempfile
from unittest.mock import MagicMock, patch
import pytest

from job_monitor.config import AppConfig, DashboardConfig, load_config
from job_monitor.notifications.desktop_macos import MacOSDesktopNotifier, build_notification_summary
from job_monitor.notifications.desktop_windows import WindowsDesktopNotifier
from job_monitor.notifications.composite import CompositeNotifier
from job_monitor.pipeline_runner import OperationalPipelineRunner
from job_monitor.ingestion import IngestionSummary, SourceIngestionStats


class TestCanonicalDashboardConfig:
    def test_canonical_dashboard_host_port_defaults(self):
        """Verifies single canonical dashboard host (127.0.0.1) and port (8500) configuration."""
        cfg = DashboardConfig()
        assert cfg.host == "127.0.0.1"
        assert cfg.port == 8500
        assert cfg.canonical_url == "http://127.0.0.1:8500"

    def test_app_config_includes_canonical_dashboard(self):
        """Verifies AppConfig includes canonical dashboard settings."""
        app_cfg = load_config()
        assert app_cfg.dashboard.host == "127.0.0.1"
        assert app_cfg.dashboard.port == 8500
        assert app_cfg.dashboard.canonical_url == "http://127.0.0.1:8500"

    def test_dashboard_config_env_overrides(self, monkeypatch):
        """Verifies environment variable overrides for DASHBOARD_HOST and DASHBOARD_PORT."""
        monkeypatch.setenv("DASHBOARD_HOST", "localhost")
        monkeypatch.setenv("DASHBOARD_PORT", "9000")

        cfg = load_config()
        assert cfg.dashboard.host == "localhost"
        assert cfg.dashboard.port == 9000
        assert cfg.dashboard.canonical_url == "http://localhost:9000"


class TestNotificationSummaryFormatting:
    def test_summary_with_new_jobs_and_strong_matches(self):
        """Tests notification summary string formatting when new jobs exist."""
        res = build_notification_summary(
            total_new=5,
            total_updated=0,
            strong_match_count=3,
            fast_cash_count=1,
            top_fast_cash_title=None,
        )
        assert res is not None
        title, message, subtitle = res
        assert title == "Ann's Job Intelligence"
        assert message == "5 new relevant jobs · 3 strong matches · 1 fastest-cash opportunity"
        assert subtitle == "Open Dashboard"

    def test_summary_with_optional_fastest_cash_title(self):
        """Tests notification summary containing optional fastest-cash job title."""
        res = build_notification_summary(
            total_new=5,
            total_updated=0,
            strong_match_count=3,
            fast_cash_count=1,
            top_fast_cash_title="Senior Contract Engineer",
        )
        assert res is not None
        title, message, subtitle = res
        assert "Fastest cash: Senior Contract Engineer" in message

    def test_summary_with_updated_jobs_only(self):
        """Tests notification summary formatting when no new jobs exist but jobs were updated."""
        res = build_notification_summary(
            total_new=0,
            total_updated=14,
            strong_match_count=2,
            fast_cash_count=0,
        )
        assert res is not None
        title, message, subtitle = res
        assert message == "14 relevant jobs updated · 2 strong matches"

    def test_no_notification_when_no_meaningful_changes(self):
        """Verifies NO notification is generated when total_new=0 and total_updated=0."""
        res = build_notification_summary(
            total_new=0,
            total_updated=0,
            strong_match_count=5,
            fast_cash_count=2,
        )
        assert res is None


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS-specific desktop notifier tests")
class TestMacOSDesktopNotifier:
    def test_find_terminal_notifier_discovery(self):
        """Verifies find_terminal_notifier locates installed terminal-notifier binary."""
        from job_monitor.notifications.desktop_macos import find_terminal_notifier
        path = find_terminal_notifier()
        assert path is not None
        assert "terminal-notifier" in path

    def test_notification_command_construction(self):
        """Tests osascript command construction for native macOS notification banner."""
        notifier = MacOSDesktopNotifier(sound_name="Glass", dashboard_url="http://127.0.0.1:8500")
        notifier.terminal_notifier_path = None  # Force osascript fallback testing
        cmd = notifier.build_notification_command(
            title="Ann's Job Intelligence",
            message="5 new relevant jobs · 3 strong matches",
            subtitle="Open Dashboard",
        )
        assert cmd[0] == "osascript"
        assert cmd[1] == "-e"
        assert 'display notification "5 new relevant jobs · 3 strong matches" with title "Ann\'s Job Intelligence" subtitle "Open Dashboard" sound name "Glass"' in cmd[2]
        assert "display alert" not in cmd[2]

    def test_terminal_notifier_command_construction(self):
        """Tests terminal-notifier command construction when terminal-notifier binary exists."""
        notifier = MacOSDesktopNotifier(sound_name="Glass", dashboard_url="http://127.0.0.1:8500")
        notifier.terminal_notifier_path = "/usr/local/bin/terminal-notifier"
        cmd = notifier.build_notification_command(
            title="Ann's Job Intelligence",
            message="5 new relevant jobs · 3 strong matches",
            subtitle="Open Dashboard",
        )
        assert cmd[0] == "/usr/local/bin/terminal-notifier"
        assert "-title" in cmd and "Ann's Job Intelligence" in cmd
        assert "-open" in cmd and "http://127.0.0.1:8500" in cmd

    @patch("subprocess.run")
    def test_open_dashboard_url_invocation(self, mock_run):
        """Tests launching the canonical dashboard URL in browser via browser tab focus and open fallback."""
        mock_run.return_value = MagicMock(returncode=0, stdout="false")
        notifier = MacOSDesktopNotifier(dashboard_url="http://127.0.0.1:8500")

        res = notifier.open_dashboard_url()
        assert res is True
        calls = [c[0][0] for c in mock_run.call_args_list if c[0] and isinstance(c[0][0], list)]
        assert any("open" in cmd for cmd in calls)

    @patch("subprocess.run")
    def test_send_notification_auto_open(self, mock_run):
        """Tests sending notification with auto_open flag triggering open command."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        notifier = MacOSDesktopNotifier(dashboard_url="http://127.0.0.1:8500")

        with patch.object(notifier, "open_dashboard_url") as mock_open:
            success = notifier.send_notification(
                title="Ann's Job Intelligence",
                message="5 new relevant jobs",
                auto_open=True,
            )
            assert success is True
            mock_open.assert_called_once()




class TestPipelineNotificationIntegration:
    @patch("job_monitor.pipeline_runner.IngestionPipeline.run")
    @patch.object(CompositeNotifier, "send_notification")
    def test_pipeline_triggers_notification_on_new_jobs(self, mock_send_notif, mock_pipeline_run):
        """Verifies operational pipeline constructs and dispatches notification when new jobs are ingested."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            db_path = tf.name

        try:
            mock_summary = IngestionSummary(
                total_new=3,
                total_updated=1,
                sources={
                    "remotive": SourceIngestionStats(source_name="remotive", fetched=10, new=3, updated=1)
                }
            )
            mock_pipeline_run.return_value = mock_summary

            os.environ["DATABASE_PATH"] = db_path
            runner = OperationalPipelineRunner()

            runner.run_full_cycle()
            assert mock_send_notif.called
            args, kwargs = mock_send_notif.call_args
            title = kwargs.get("title") or args[0]
            message = kwargs.get("message") or args[1]
            assert title == "Ann's Job Intelligence"
            assert "3 new relevant jobs" in message

        finally:
            if "DATABASE_PATH" in os.environ:
                del os.environ["DATABASE_PATH"]
            if os.path.exists(db_path):
                os.remove(db_path)

    @patch("job_monitor.pipeline_runner.IngestionPipeline.run")
    @patch.object(CompositeNotifier, "send_notification")
    def test_pipeline_skips_notification_on_zero_changes(self, mock_send_notif, mock_pipeline_run):
        """Verifies operational pipeline skips sending notification when there are zero new or updated jobs."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            db_path = tf.name

        try:
            mock_summary = IngestionSummary(
                sources={
                    "remotive": SourceIngestionStats(source_name="remotive", fetched=10, new=0, updated=0)
                }
            )
            mock_pipeline_run.return_value = mock_summary

            os.environ["DATABASE_PATH"] = db_path
            runner = OperationalPipelineRunner()

            runner.run_full_cycle()
            assert not mock_send_notif.called

        finally:
            if "DATABASE_PATH" in os.environ:
                del os.environ["DATABASE_PATH"]
            if os.path.exists(db_path):
                os.remove(db_path)


@pytest.mark.parametrize("target_platform,expected_notifier_cls", [
    ("win32", WindowsDesktopNotifier),
    ("darwin", MacOSDesktopNotifier),
    ("linux", None),
])
def test_get_platform_notifier_selection(target_platform, expected_notifier_cls):
    """Verifies get_platform_notifier selects platform-appropriate desktop notifier."""
    from job_monitor.notifications import MacOSDesktopNotifier, WindowsDesktopNotifier, get_platform_notifier

    notifier = get_platform_notifier(target_platform=target_platform)

    if expected_notifier_cls is None:
        assert len(notifier.notifiers) == 0
    else:
        assert len(notifier.notifiers) == 1
        assert isinstance(notifier.notifiers[0], expected_notifier_cls)






