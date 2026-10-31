"""Unit tests for Phase 16C — macOS LaunchAgent and Windows Task Scheduler builders."""

import sys
import pytest
from job_monitor.scheduler.macos_scheduler import MacOSLaunchdScheduler
from job_monitor.scheduler.windows_scheduler import WindowsTaskScheduler


def test_macos_scheduler_plist_dict(tmp_path):
    """Verifies that MacOSLaunchdScheduler generates valid plist dictionary."""
    scheduler = MacOSLaunchdScheduler(executable_path="/Applications/AnnsJobTracker.app/Contents/MacOS/job-monitor")
    plist_dict = scheduler.generate_plist_dict(hour=8, minute=0)

    assert plist_dict["Label"] == "com.annsjobtracker.monitor"
    assert plist_dict["ProgramArguments"] == [
        "/Applications/AnnsJobTracker.app/Contents/MacOS/job-monitor",
        "run",
        "--scheduled",
    ]
    assert plist_dict["StartCalendarInterval"] == {"Hour": 8, "Minute": 0}
    assert plist_dict["RunAtLoad"] is True
    assert "launchd_stdout.log" in plist_dict["StandardOutPath"]


def test_windows_scheduler_init(tmp_path):
    """Verifies WindowsTaskScheduler initialization and executable detection."""
    scheduler = WindowsTaskScheduler(executable_path="C:\\Program Files\\AnnsJobTracker\\AnnsJobTracker.exe")
    assert scheduler.task_name == "AnnsJobTracker_DailyMonitor"
    assert scheduler.executable_path == "C:\\Program Files\\AnnsJobTracker\\AnnsJobTracker.exe"
