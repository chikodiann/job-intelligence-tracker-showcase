"""Windows Task Scheduler management for 8:00 AM daily job-monitor runs with missed-run recovery."""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from ..utils.logging import setup_logger

logger = setup_logger("scheduler.windows")

TASK_NAME = "AnnsJobTracker_DailyMonitor"


class WindowsTaskScheduler:
    """Manages Windows Task Scheduler task for daily 8:00 AM job monitoring runs."""

    def __init__(self, executable_path: Optional[str] = None):
        self.task_name = TASK_NAME
        self.executable_path = executable_path or self._detect_executable()

    def _detect_executable(self) -> str:
        """Detects binary path to execute in Windows Task Scheduler."""
        if getattr(sys, "frozen", False):
            return str(Path(sys.executable))
        return sys.executable

    def install_schedule(self, hour: int = 8, minute: int = 0) -> bool:
        """Registers Windows Scheduled Task set for daily 8:00 AM run with missed-run recovery enabled."""
        if sys.platform != "win32":
            logger.warning("Windows Task Scheduler is only supported on Windows platform.")
            return False

        try:
            start_time = f"{hour:02d}:{minute:02d}"
            target_exe = self.executable_path

            # Use PowerShell Register-ScheduledTask to set StartWhenAvailable = $true (missed-run recovery)
            ps_script = f"""
            $action = New-ScheduledTaskAction -Execute '{target_exe}' -Argument 'run --scheduled'
            $trigger = New-ScheduledTaskTrigger -Daily -At '{start_time}'
            $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
            Register-ScheduledTask -TaskName '{self.task_name}' -Action $action -Trigger $trigger -Settings $settings -Force
            """

            cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if res.returncode == 0:
                logger.info("Successfully installed Windows Task Scheduler task '%s' at %s", self.task_name, start_time)
                return True
            else:
                logger.error("PowerShell Register-ScheduledTask failed (code %d): %s", res.returncode, res.stderr)
                return False
        except Exception as e:
            logger.error("Failed to install Windows Task Scheduler task: %s", str(e))
            return False

    def uninstall_schedule(self) -> bool:
        """Unregisters Windows Scheduled Task."""
        if sys.platform != "win32":
            return False
        try:
            cmd = ["schtasks", "/Delete", "/TN", self.task_name, "/F"]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                logger.info("Successfully uninstalled Windows Task Scheduler task '%s'.", self.task_name)
                return True
            return False
        except Exception as e:
            logger.error("Failed to uninstall Windows Task Scheduler task: %s", str(e))
            return False

    def is_installed(self) -> bool:
        """Checks if Scheduled Task is registered."""
        if sys.platform != "win32":
            return False
        res = subprocess.run(["schtasks", "/Query", "/TN", self.task_name], capture_output=True, text=True)
        return res.returncode == 0
