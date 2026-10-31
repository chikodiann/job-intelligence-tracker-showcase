"""macOS Single-Instance Management, Process Lifecycle, & Tab Reuse Engine."""

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .logging import setup_logger
from .paths import AppPaths

logger = setup_logger("utils.single_instance")


def get_runtime_metadata_path() -> Path:
    """Returns path to application's established per-user runtime metadata JSON file."""
    return AppPaths.get_user_data_dir() / "runtime_instance.json"


def is_process_running(pid: int) -> bool:
    """Validates if process with given PID is currently active on the host OS."""
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if handle:
                exit_code = ctypes.c_ulong()
                if kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                    kernel32.CloseHandle(handle)
                    return exit_code.value == 259  # STILL_ACTIVE
                kernel32.CloseHandle(handle)
            return False
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError, PermissionError):
            return False


def ping_server_health(port: int, retries: int = 3, timeout_sec: float = 0.5) -> bool:
    """Pings HTTP health endpoint (/api/pipeline/status) with brief retries to confirm active server."""
    health_url = f"http://127.0.0.1:{port}/api/pipeline/status"
    for attempt in range(retries):
        try:
            req = urllib.request.Request(health_url, headers={"User-Agent": "AnnsJobTracker-SingleInstanceCheck"})
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        if attempt < retries - 1:
            time.sleep(0.3)
    return False


def focus_or_open_dashboard_tab(url: str) -> bool:
    """Reuses/focuses existing dashboard tab in Chrome, Safari, Brave, or Edge via AppleScript on macOS, falling back to open."""
    if sys.platform != "darwin":
        try:
            webbrowser.open(url)
            return True
        except Exception as e:
            logger.error("Failed to open browser on non-macOS platform: %s", str(e))
            return False

    parsed = urllib.parse.urlparse(url)
    target_match = parsed.netloc or f"{parsed.hostname}:{parsed.port}"

    applescript = f'''
    set targetUrlMatch to "{target_match}"
    set tabFound to false

    -- Try Google Chrome
    try
        if application "Google Chrome" is running then
            tell application "Google Chrome"
                repeat with w in windows
                    set tabIndex to 1
                    repeat with t in tabs of w
                        if URL of t contains targetUrlMatch then
                            set active tab index of w to tabIndex
                            set index of w to 1
                            activate
                            set tabFound to true
                            exit repeat
                        end if
                        set tabIndex to tabIndex + 1
                    end repeat
                    if tabFound then exit repeat
                end repeat
            end tell
        end if
    on error
    end try

    -- Try Safari
    if not tabFound then
        try
            if application "Safari" is running then
                tell application "Safari"
                    repeat with w in windows
                        repeat with t in tabs of w
                            if URL of t contains targetUrlMatch then
                                set current tab of w to t
                                set index of w to 1
                                activate
                                set tabFound to true
                                exit repeat
                            end if
                        end repeat
                        if tabFound then exit repeat
                    end repeat
                end tell
            end if
        on error
        end try
    end if

    -- Try Brave Browser
    if not tabFound then
        try
            if application "Brave Browser" is running then
                tell application "Brave Browser"
                    repeat with w in windows
                        set tabIndex to 1
                        repeat with t in tabs of w
                            if URL of t contains targetUrlMatch then
                                set active tab index of w to tabIndex
                                set index of w to 1
                                activate
                                set tabFound to true
                                exit repeat
                            end if
                            set tabIndex to tabIndex + 1
                        end repeat
                        if tabFound then exit repeat
                    end repeat
                end tell
            end if
        on error
        end try
    end if

    -- Try Microsoft Edge
    if not tabFound then
        try
            if application "Microsoft Edge" is running then
                tell application "Microsoft Edge"
                    repeat with w in windows
                        set tabIndex to 1
                        repeat with t in tabs of w
                            if URL of t contains targetUrlMatch then
                                set active tab index of w to tabIndex
                                set index of w to 1
                                activate
                                set tabFound to true
                                exit repeat
                            end if
                            set tabIndex to tabIndex + 1
                        end repeat
                        if tabFound then exit repeat
                    end repeat
                end tell
            end if
        on error
        end try
    end if

    return tabFound
    '''

    try:
        res = subprocess.run(["osascript", "-e", applescript], capture_output=True, text=True, timeout=4)
        if res.returncode == 0 and "true" in res.stdout.lower():
            logger.info("Successfully focused existing dashboard tab via AppleScript for %s", target_match)
            return True
    except Exception as e:
        logger.debug("AppleScript tab focus encountered error or permission limitation: %s", str(e))

    # Standard fallback to open command or webbrowser
    try:
        res = subprocess.run(["open", url], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            logger.info("Opened dashboard URL via macOS open command: %s", url)
            return True
        webbrowser.open(url)
        return True
    except Exception as e:
        logger.error("Failed to open dashboard URL via fallback: %s", str(e))
        return False


class SingleInstanceManager:
    """Manages single-instance lifecycle, runtime metadata, health verification, and secondary launch activation."""

    @classmethod
    def get_runtime_metadata(cls) -> Optional[Dict[str, Any]]:
        """Reads runtime metadata JSON file if it exists and is valid JSON."""
        meta_path = get_runtime_metadata_path()
        if not meta_path.exists():
            return None
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "port" in data:
                return data
        except Exception as e:
            logger.warning("Stale or invalid runtime metadata file at %s: %s", meta_path, str(e))
        return None

    @classmethod
    def is_instance_active(cls, profile_name: Optional[str] = None, retries: int = 3) -> Optional[Dict[str, Any]]:
        """Validates recorded process PID AND HTTP health ping.

        Returns metadata dict if instance is active, healthy, and matches requested profile (if specified).
        Cleans up stale metadata file if the recorded PID is dead AND health check fails.
        """
        meta = cls.get_runtime_metadata()
        if not meta:
            return None

        # Profile isolation check: if a specific profile is requested, ensure active instance matches
        if profile_name and meta.get("profile"):
            active_prof = str(meta.get("profile")).strip().lower()
            requested_prof = str(profile_name).strip().lower()
            if active_prof != requested_prof:
                logger.info(
                    "Active instance found for profile '%s', but requested profile is '%s'. Profile isolation enforced.",
                    active_prof,
                    requested_prof,
                )
                return None

        pid = meta.get("pid", 0)
        port = meta.get("port", 8500)

        pid_alive = is_process_running(pid)
        server_healthy = ping_server_health(port, retries=retries, timeout_sec=0.8)

        if pid_alive or server_healthy:
            logger.info("Active instance confirmed: PID %d (alive=%s) on port %d (healthy=%s)", pid, pid_alive, port, server_healthy)
            return meta

        logger.info("Stale instance metadata detected (PID %d dead, port %d unreachable). Cleaning up lock.", pid, port)
        cls.cleanup_metadata()
        return None

    @classmethod
    def register_instance(cls, port: int, profile_name: Optional[str] = None) -> Dict[str, Any]:
        """Registers runtime instance metadata file in per-user data directory."""
        meta_path = get_runtime_metadata_path()
        data = {
            "pid": os.getpid(),
            "port": port,
            "url": f"http://127.0.0.1:{port}",
            "profile": profile_name or "default",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            meta_path.parent.mkdir(parents=True, exist_ok=True)
            meta_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            logger.info("Registered runtime instance metadata: PID %d on port %d at %s", os.getpid(), port, meta_path)
        except Exception as e:
            logger.error("Failed to write runtime instance metadata: %s", str(e))
        return data

    @classmethod
    def cleanup_metadata(cls) -> None:
        """Removes runtime instance metadata file safely."""
        meta_path = get_runtime_metadata_path()
        try:
            if meta_path.exists():
                meta_path.unlink()
                logger.info("Cleaned up runtime instance metadata file.")
        except Exception as e:
            logger.error("Error deleting runtime instance metadata file: %s", str(e))

    @classmethod
    def activate_instance(cls, instance_meta: Dict[str, Any]) -> bool:
        """Sends loopback POST /api/activate request or focuses browser tab for active instance."""
        port = instance_meta.get("port", 8500)
        url = instance_meta.get("url", f"http://127.0.0.1:{port}")
        activate_url = f"http://127.0.0.1:{port}/api/activate"

        try:
            req = urllib.request.Request(
                activate_url,
                data=json.dumps({"action": "activate"}).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "AnnsJobTracker-SecondaryLaunch"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    logger.info("Secondary launch activated existing instance via HTTP POST /api/activate")
                    return True
        except Exception as e:
            logger.debug("Loopback /api/activate POST error: %s. Falling back to direct tab focus.", str(e))

        # Direct local browser focus fallback
        return focus_or_open_dashboard_tab(url)
