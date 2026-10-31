"""Unit and integration tests for Phase 16D — Desktop App Launch Lifecycle & Notification Integration."""

import time
from unittest.mock import MagicMock, patch
import pytest

from job_monitor.cli import main as cli_main
from job_monitor.dashboard.server import DashboardServer, get_runtime_dashboard_url, set_runtime_dashboard_url
from job_monitor.notifications.desktop_macos import MacOSDesktopNotifier


def test_cli_explicit_run_remains_batch_mode():
    """Verifies that `job-monitor run` remains batch execution (does not start long-running server)."""
    with patch("job_monitor.cli.OperationalPipelineRunner") as MockRunner:
        mock_runner_inst = MagicMock()
        mock_runner_inst.run_full_cycle.return_value = "Mock Report Text"
        MockRunner.return_value = mock_runner_inst

        cli_main(["run"])

        MockRunner.assert_called_once()
        mock_runner_inst.run_full_cycle.assert_called_once()


def test_desktop_launch_no_args_starts_server_first_and_runs_bg_pipeline():
    """Verifies that launching CLI with no arguments (Desktop App Mode):
    1. Binds server first and sets runtime dashboard URL.
    2. Runs pipeline in background worker.
    3. Enters server.run_forever(open_browser=False).
    """
    call_order = []

    with patch("job_monitor.cli.SingleInstanceManager.is_instance_active", return_value=None), \
         patch("job_monitor.cli.DashboardServer") as MockServerClass, \
         patch("job_monitor.cli.OperationalPipelineRunner") as MockRunnerClass, \
         patch("job_monitor.cli.threading.Thread") as MockThreadClass:

        mock_server = MagicMock()
        mock_httpd = MagicMock()
        mock_server._bind_server.side_effect = lambda: (call_order.append("bind_server"), mock_httpd)[1]
        mock_server.run_forever.side_effect = lambda **kwargs: call_order.append("run_forever")
        MockServerClass.return_value = mock_server

        mock_thread = MagicMock()
        MockThreadClass.side_effect = lambda target, daemon: (call_order.append("thread_created"), mock_thread)[1]

        cli_main([])

        # Verify call sequence
        assert "bind_server" in call_order
        assert "thread_created" in call_order
        assert "run_forever" in call_order
        assert call_order.index("bind_server") < call_order.index("thread_created")
        assert call_order.index("thread_created") < call_order.index("run_forever")

        mock_server.run_forever.assert_called_once_with(open_browser=False)


def test_notification_captures_actual_bound_runtime_url():
    """Verifies that notification receives the actual bound runtime dashboard URL (including dynamic ports)."""
    import sys
    from job_monitor.notifications import get_platform_notifier
    original_url = get_runtime_dashboard_url()
    try:
        set_runtime_dashboard_url("http://127.0.0.1:8542")
        notifier = get_platform_notifier().notifiers[0] if get_platform_notifier().notifiers else MacOSDesktopNotifier()
        assert notifier.dashboard_url == "http://127.0.0.1:8542"

        if sys.platform == "darwin":
            with patch("job_monitor.notifications.desktop_macos.find_terminal_notifier", return_value="/usr/local/bin/terminal-notifier"):
                cmd = notifier.build_notification_command("Title", "Message", "Subtitle")
                assert "-open" in cmd
                open_idx = cmd.index("-open")
                assert cmd[open_idx + 1] == "http://127.0.0.1:8542"
    finally:
        set_runtime_dashboard_url(original_url)


def test_dynamic_port_fallback_updates_runtime_url(tmp_path):
    """Verifies that when preferred port is in use, DashboardServer falls back to next port and updates runtime URL."""
    import socket
    import sys
    original_url = get_runtime_dashboard_url()

    # Dynamically find and block an ephemeral port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if sys.platform == "win32":
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        except (AttributeError, OSError):
            pass
    else:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    test_port = sock.getsockname()[1]
    sock.listen(1)

    try:
        db_file = tmp_path / "test.db"
        server = DashboardServer(host="127.0.0.1", port=test_port, db_path=str(db_file))
        httpd = server._bind_server()

        try:
            assert server.port == test_port + 1
            assert get_runtime_dashboard_url() == f"http://127.0.0.1:{test_port + 1}"
        finally:
            httpd.server_close()
    finally:
        sock.close()
        set_runtime_dashboard_url(original_url)

