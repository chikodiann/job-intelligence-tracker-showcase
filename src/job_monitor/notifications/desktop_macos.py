"""macOS Desktop Notification provider with dashboard integration via native osascript/AppleScript or terminal-notifier."""

import os
import shutil
import subprocess
import sys
import webbrowser
from typing import Any, List, Optional, Tuple

from ..config import load_config
from ..interfaces.notifier import BaseNotifier, JobScoreResult
from ..models.normalized_job import NormalizedJob
from ..utils.logging import setup_logger

logger = setup_logger("notifications.macos")


def find_terminal_notifier() -> Optional[str]:
    """Finds path to terminal-notifier executable if installed on macOS."""
    path = shutil.which("terminal-notifier")
    if path and os.path.exists(path):
        return path
    for candidate in ["/opt/homebrew/bin/terminal-notifier", "/usr/local/bin/terminal-notifier"]:
        if os.path.exists(candidate):
            return candidate
    return None


def build_notification_summary(
    total_new: int = 0,
    total_updated: int = 0,
    strong_match_count: int = 0,
    fast_cash_count: int = 0,
    top_fast_cash_title: Optional[str] = None,
) -> Optional[Tuple[str, str, str]]:
    """Constructs (title, message, subtitle) tuple for macOS notification.

    Returns None if there are no meaningful changes (total_new == 0 and total_updated == 0).
    """
    if total_new == 0 and total_updated == 0:
        return None

    title = "Ann's Job Intelligence"
    subtitle = "Open Dashboard"

    parts = []
    if total_new > 0:
        parts.append(f"{total_new} new relevant job{'s' if total_new != 1 else ''}")
    elif total_updated > 0:
        parts.append(f"{total_updated} relevant job{'s' if total_updated != 1 else ''} updated")

    if strong_match_count > 0:
        parts.append(f"{strong_match_count} strong match{'es' if strong_match_count != 1 else ''}")

    if top_fast_cash_title and top_fast_cash_title.strip():
        clean_title = top_fast_cash_title.strip()
        if len(clean_title) > 30:
            clean_title = clean_title[:27] + "..."
        parts.append(f"Fastest cash: {clean_title}")
    elif fast_cash_count > 0:
        parts.append(f"{fast_cash_count} fastest-cash opportunit{'ies' if fast_cash_count != 1 else 'y'}")

    message = " · ".join(parts)
    return title, message, subtitle


class MacOSDesktopNotifier(BaseNotifier):
    """macOS Desktop Notification provider using terminal-notifier (primary) or osascript (fallback)."""

    def __init__(self, sound_name: str = "Glass", dashboard_url: Optional[str] = None):
        self.sound_name = sound_name
        self.explicit_dashboard_url = dashboard_url
        self.terminal_notifier_path = find_terminal_notifier()

    @property
    def dashboard_url(self) -> str:
        if self.explicit_dashboard_url:
            return self.explicit_dashboard_url
        from ..dashboard.server import get_runtime_dashboard_url
        return get_runtime_dashboard_url()

    def open_dashboard_url(self, url: Optional[str] = None) -> bool:
        """Launches or focuses canonical dashboard URL in browser using browser-aware tab reuse."""
        target_url = url or self.dashboard_url
        from ..utils.single_instance import focus_or_open_dashboard_tab
        return focus_or_open_dashboard_tab(target_url)

    def send_notification(self, title: str, message: str, subtitle: Optional[str] = None, auto_open: bool = False) -> bool:
        """Sends native macOS top-right desktop notification via terminal-notifier or osascript."""
        if sys.platform != "darwin":
            logger.warning("macOS desktop notifications are only supported on macOS platform.")
            return False

        try:
            cmd = self.build_notification_command(title, message, subtitle)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5,
            )
            success = result.returncode == 0
            if success:
                logger.info("macOS Desktop notification sent successfully: %s - %s", title, message)
                if auto_open:
                    self.open_dashboard_url()
                return True
            else:
                logger.error("Notification command failed with code %d: %s", result.returncode, result.stderr)
                return False
        except Exception as e:
            logger.error("Failed to send macOS desktop notification: %s", str(e))
            return False

    def send_digest(self, ranked_matches: List[Tuple[NormalizedJob, JobScoreResult]]) -> bool:
        """Sends summary digest notification for top job matches."""
        count = len(ranked_matches)
        if count == 0:
            return True  # Avoid noisy notification when zero matches exist

        top_job = ranked_matches[0][0]
        title = "Ann's Job Intelligence"
        subtitle = f"{count} Relevant Opportunities Identified"
        message = f"Top Match: {top_job.title} @ {top_job.company_name}"
        return self.send_notification(title, message, subtitle)

    def build_notification_command(self, title: str, message: str, subtitle: Optional[str] = None) -> List[str]:
        """Constructs CLI command tuple for terminal-notifier or osascript."""
        safe_title = title.replace('"', '\\"')
        safe_message = message.replace('"', '\\"')
        safe_subtitle = (subtitle or "").replace('"', '\\"')

        # If terminal-notifier is available, use it for native top-right banner with click-to-open URL
        if self.terminal_notifier_path:
            cmd = [
                self.terminal_notifier_path,
                "-title", title,
                "-message", message,
                "-open", self.dashboard_url,
            ]
            if subtitle:
                cmd.extend(["-subtitle", subtitle])
            if self.sound_name:
                cmd.extend(["-sound", self.sound_name])
            return cmd

        # Native macOS fallback: osascript AppleScript display notification (top-right banner only)
        script = f'display notification "{safe_message}" with title "{safe_title}"'
        if safe_subtitle:
            script += f' subtitle "{safe_subtitle}"'
        if self.sound_name:
            script += f' sound name "{self.sound_name}"'

        return ["osascript", "-e", script]
