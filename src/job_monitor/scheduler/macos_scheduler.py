"""macOS launchd LaunchAgent scheduler management for 8:00 AM daily job-monitor runs."""

import os
import plistlib
import subprocess
import sys
from pathlib import Path
from typing import Optional

from ..utils.logging import setup_logger

logger = setup_logger("scheduler.macos")

PLIST_LABEL = "com.annsjobtracker.monitor"


class MacOSLaunchdScheduler:
    """Manages launchd LaunchAgent plist for daily 8:00 AM job monitoring runs."""

    def __init__(self, executable_path: Optional[str] = None):
        self.label = PLIST_LABEL
        self.plist_path = Path.home() / "Library" / "LaunchAgents" / f"{self.label}.plist"
        self.executable_path = executable_path or self._detect_executable()

    def _detect_executable(self) -> str:
        """Detects binary path to execute in launchd (packaged app binary or python CLI)."""
        if getattr(sys, "frozen", False):
            # In PyInstaller app bundle
            exe = Path(sys.executable)
            return str(exe)
        # Development mode
        venv_bin = Path(__file__).resolve().parent.parent.parent.parent / ".venv" / "bin" / "job-monitor"
        if venv_bin.exists():
            return str(venv_bin)
        return sys.executable

    def generate_plist_dict(self, hour: int = 8, minute: int = 0) -> dict:
        """Constructs LaunchAgent dictionary for 8:00 AM daily run with missed run recovery."""
        from ..utils.paths import AppPaths

        logs_dir = AppPaths.get_logs_dir()
        stdout_log = str(logs_dir / "launchd_stdout.log")
        stderr_log = str(logs_dir / "launchd_stderr.log")

        return {
            "Label": self.label,
            "ProgramArguments": [
                self.executable_path,
                "run",
                "--scheduled",
            ],
            "StartCalendarInterval": {
                "Hour": hour,
                "Minute": minute,
            },
            "RunAtLoad": True,  # Ensures missed morning run triggers on wake/boot if not run today
            "StandardOutPath": stdout_log,
            "StandardErrorPath": stderr_log,
        }

    def install_schedule(self, hour: int = 8, minute: int = 0) -> bool:
        """Generates and registers LaunchAgent plist with launchctl."""
        if sys.platform != "darwin":
            logger.warning("macOS launchd scheduling is only supported on macOS platform.")
            return False

        try:
            self.plist_path.parent.mkdir(parents=True, exist_ok=True)
            plist_data = self.generate_plist_dict(hour=hour, minute=minute)

            with open(self.plist_path, "wb") as f:
                plistlib.dump(plist_data, f)

            # Unload previous if loaded
            subprocess.run(["launchctl", "unload", str(self.plist_path)], capture_output=True)
            # Load new plist
            res = subprocess.run(["launchctl", "load", str(self.plist_path)], capture_output=True, text=True)

            if res.returncode == 0:
                logger.info("Successfully installed macOS launchd schedule at %02d:%02d: %s", hour, minute, self.plist_path)
                return True
            else:
                logger.error("launchctl load failed (code %d): %s", res.returncode, res.stderr)
                return False
        except Exception as e:
            logger.error("Failed to install macOS launchd schedule: %s", str(e))
            return False

    def uninstall_schedule(self) -> bool:
        """Unloads and removes LaunchAgent plist file."""
        if sys.platform != "darwin":
            return False
        try:
            if self.plist_path.exists():
                subprocess.run(["launchctl", "unload", str(self.plist_path)], capture_output=True)
                self.plist_path.unlink()
                logger.info("Successfully uninstalled macOS launchd schedule.")
                return True
            return True
        except Exception as e:
            logger.error("Failed to uninstall macOS launchd schedule: %s", str(e))
            return False

    def is_installed(self) -> bool:
        """Checks if LaunchAgent plist file exists and launchctl lists it."""
        if not self.plist_path.exists():
            return False
        res = subprocess.run(["launchctl", "list", self.label], capture_output=True, text=True)
        return res.returncode == 0
