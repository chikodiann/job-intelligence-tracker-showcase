"""Windows Desktop Notification provider using PowerShell Toast Notifications or fallback provider."""

import os
import subprocess
import sys
import webbrowser
from typing import List, Optional, Tuple

from ..interfaces.notifier import BaseNotifier, JobScoreResult
from ..models.normalized_job import NormalizedJob
from ..utils.logging import setup_logger

logger = setup_logger("notifications.windows")


class WindowsDesktopNotifier(BaseNotifier):
    """Windows Desktop Notification provider using PowerShell toast notifications."""

    def __init__(self, sound_name: str = "Default", dashboard_url: Optional[str] = None):
        self.sound_name = sound_name
        self.explicit_dashboard_url = dashboard_url

    @property
    def dashboard_url(self) -> str:
        if self.explicit_dashboard_url:
            return self.explicit_dashboard_url
        from ..dashboard.server import get_runtime_dashboard_url
        return get_runtime_dashboard_url()

    def open_dashboard_url(self, url: Optional[str] = None) -> bool:
        """Launches dashboard URL in default Windows browser."""
        target_url = url or self.dashboard_url
        try:
            webbrowser.open(target_url)
            logger.info("Opened Windows dashboard URL in browser: %s", target_url)
            return True
        except Exception as e:
            logger.error("Failed to open Windows dashboard URL %s: %s", target_url, str(e))
            return False

    def send_notification(self, title: str, message: str, subtitle: Optional[str] = None, auto_open: bool = False) -> bool:
        """Sends Windows desktop notification via PowerShell BurntToast / System notification API."""
        if sys.platform != "win32":
            logger.warning("Windows desktop notifications are only supported on Windows platform.")
            return False

        try:
            safe_title = title.replace('"', '`"')
            safe_message = message.replace('"', '`"')
            target_url = self.dashboard_url

            # PowerShell command for Windows 10/11 Toast Notification
            ps_script = f"""
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
            [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocumentData, ContentType = WindowsRuntime] | Out-Null
            $template = @"
            <toast launch="{target_url}">
                <visual>
                    <binding template="ToastGeneric">
                        <text>{safe_title}</text>
                        <text>{safe_message}</text>
                    </binding>
                </visual>
            </toast>
            "@
            $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
            $xml.LoadXml($template)
            $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("AnnsJobTracker").Show($toast)
            """

            cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

            if res.returncode == 0:
                logger.info("Windows desktop notification sent successfully: %s", title)
                if auto_open:
                    self.open_dashboard_url()
                return True
            else:
                logger.warning("PowerShell toast notification failed (code %d), falling back to browser launch", res.returncode)
                return False
        except Exception as e:
            logger.error("Error sending Windows desktop notification: %s", str(e))
            return False

    def send_digest(self, ranked_matches: List[Tuple[NormalizedJob, JobScoreResult]]) -> bool:
        """Sends summary digest notification for top job matches."""
        count = len(ranked_matches)
        if count == 0:
            return True
        top_job = ranked_matches[0][0]
        title = "Job Intelligence"
        subtitle = f"{count} Relevant Opportunities Identified"
        message = f"Top Match: {top_job.title} @ {top_job.company_name}"
        return self.send_notification(title, message, subtitle)
