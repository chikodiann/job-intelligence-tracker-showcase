"""Unit tests for Phase 16C — Dashboard Port Propagation and Fallback."""

import socket
import pytest
from job_monitor.dashboard.server import DashboardServer, get_runtime_dashboard_url, set_runtime_dashboard_url
from job_monitor.notifications.desktop_macos import MacOSDesktopNotifier
from job_monitor.notifications.desktop_windows import WindowsDesktopNotifier


def find_free_port() -> int:
    """Helper to find a currently unused port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_default_port_binding(tmp_path):
    """Verifies default binding to requested port when available."""
    port = find_free_port()
    set_runtime_dashboard_url(f"http://127.0.0.1:{port}")
    db_file = tmp_path / "test.db"
    server = DashboardServer(host="127.0.0.1", port=port, db_path=str(db_file))

    httpd = server._bind_server()
    try:
        assert server.port == port
        assert get_runtime_dashboard_url() == f"http://127.0.0.1:{port}"

        mac_notifier = MacOSDesktopNotifier()
        win_notifier = WindowsDesktopNotifier()
        assert mac_notifier.dashboard_url == f"http://127.0.0.1:{port}"
        assert win_notifier.dashboard_url == f"http://127.0.0.1:{port}"
    finally:
        httpd.server_close()


def test_port_fallback_when_busy(tmp_path):
    """Verifies that if preferred port is occupied, DashboardServer falls back to next available port and updates runtime URL."""
    start_port = find_free_port()

    # Occupy start_port with a dummy socket
    import sys
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if sys.platform == "win32":
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        except (AttributeError, OSError):
            pass
    else:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", start_port))
    sock.listen(1)

    db_file = tmp_path / "test_fallback.db"
    server = DashboardServer(host="127.0.0.1", port=start_port, db_path=str(db_file))

    try:
        httpd = server._bind_server()
        try:
            assert server.port == start_port + 1
            expected_url = f"http://127.0.0.1:{start_port + 1}"
            assert get_runtime_dashboard_url() == expected_url

            # Check notifiers inherit active fallback port URL
            mac_notifier = MacOSDesktopNotifier()
            win_notifier = WindowsDesktopNotifier()
            assert mac_notifier.dashboard_url == expected_url
            assert win_notifier.dashboard_url == expected_url
        finally:
            httpd.server_close()
    finally:
        sock.close()
