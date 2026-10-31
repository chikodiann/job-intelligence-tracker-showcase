"""Unit and integration tests for Phase 16H — macOS Single-Instance Lifecycle & Notification Tab Reuse."""

import json
import os
import sys
from unittest.mock import MagicMock, patch
import pytest

from job_monitor.utils.paths import AppPaths
from job_monitor.utils.single_instance import (
    SingleInstanceManager,
    focus_or_open_dashboard_tab,
    get_runtime_metadata_path,
    is_process_running,
    ping_server_health,
)


def test_runtime_metadata_registration_and_cleanup(tmp_path):
    """Verifies that SingleInstanceManager registers and cleans up runtime_instance.json in user data dir."""
    AppPaths.set_data_dir_override(tmp_path)
    try:
        data = SingleInstanceManager.register_instance(port=8500, profile_name="eva")
        meta_file = get_runtime_metadata_path()

        assert meta_file.exists()
        saved = json.loads(meta_file.read_text())
        assert saved["port"] == 8500
        assert saved["pid"] == os.getpid()
        assert saved["profile"] == "eva"

        SingleInstanceManager.cleanup_metadata()
        assert not meta_file.exists()
    finally:
        AppPaths.set_data_dir_override(None)


def test_is_process_running():
    """Verifies PID running check returns True for current process and False for non-existent PID."""
    assert is_process_running(os.getpid()) is True
    assert is_process_running(999999) is False


def test_ping_server_health_unreachable_port():
    """Verifies ping_server_health returns False for an unreachable port."""
    assert ping_server_health(port=59999, retries=1, timeout_sec=0.1) is False


def test_stale_lock_recovery(tmp_path):
    """Verifies stale lock file (dead PID and dead port) is cleaned up and returns None."""
    AppPaths.set_data_dir_override(tmp_path)
    try:
        meta_file = get_runtime_metadata_path()
        stale_data = {"pid": 999999, "port": 59999, "url": "http://127.0.0.1:59999", "created_at": "2026-10-09T00:00:00Z"}
        meta_file.write_text(json.dumps(stale_data), encoding="utf-8")

        active = SingleInstanceManager.is_instance_active(retries=1)
        assert active is None
        assert not meta_file.exists(), "Stale metadata file must be deleted upon discovery"
    finally:
        AppPaths.set_data_dir_override(None)


def test_healthy_instance_detection(tmp_path):
    """Verifies is_instance_active returns metadata when PID is running and server ping succeeds."""
    AppPaths.set_data_dir_override(tmp_path)
    try:
        SingleInstanceManager.register_instance(port=8500, profile_name="eva")
        with patch("job_monitor.utils.single_instance.ping_server_health", return_value=True):
            active = SingleInstanceManager.is_instance_active(retries=1)
            assert active is not None
            assert active["port"] == 8500
            assert active["pid"] == os.getpid()
    finally:
        AppPaths.set_data_dir_override(None)


def test_focus_or_open_dashboard_tab_fallback():
    """Verifies focus_or_open_dashboard_tab handles fallback gracefully on macOS and Windows."""
    if sys.platform == "darwin":
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="true")
            result = focus_or_open_dashboard_tab("http://127.0.0.1:8500")
            assert result is True
            assert mock_run.called
    else:
        with patch("webbrowser.open") as mock_webbrowser:
            mock_webbrowser.return_value = True
            result = focus_or_open_dashboard_tab("http://127.0.0.1:8500")
            assert result is True
            mock_webbrowser.assert_called_once_with("http://127.0.0.1:8500")


def test_profile_isolation_single_instance(tmp_path):
    """Verifies that is_instance_active enforces profile isolation when requesting a different profile."""
    AppPaths.set_data_dir_override(tmp_path)
    try:
        SingleInstanceManager.register_instance(port=8500, profile_name="eva")
        with patch("job_monitor.utils.single_instance.ping_server_health", return_value=True):
            # Same profile should return active metadata
            eva_active = SingleInstanceManager.is_instance_active(profile_name="eva", retries=1)
            assert eva_active is not None
            assert eva_active["profile"] == "eva"

            # Different profile should return None (isolation enforced)
            ann_active = SingleInstanceManager.is_instance_active(profile_name="ann", retries=1)
            assert ann_active is None, "Different candidate profile must NOT activate an existing instance"
    finally:
        AppPaths.set_data_dir_override(None)

