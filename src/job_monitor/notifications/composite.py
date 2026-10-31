from typing import List, Optional, Tuple
from ..interfaces.notifier import BaseNotifier, JobScoreResult
from ..models.normalized_job import NormalizedJob
from ..utils.logging import setup_logger
from .desktop_macos import MacOSDesktopNotifier

logger = setup_logger("notifications.composite")


class CompositeNotifier(BaseNotifier):
    """Composite notifier routing notifications to configured channels."""

    def __init__(self, enabled: bool = True, notifiers: Optional[List[BaseNotifier]] = None):
        self.enabled = enabled
        self.notifiers = notifiers if notifiers is not None else [MacOSDesktopNotifier()]

    def send_digest(self, ranked_matches: List[Tuple[NormalizedJob, JobScoreResult]]) -> bool:
        """Sends digest across all enabled notification channels."""
        if not self.enabled:
            logger.info("Notifications are currently disabled in configuration.")
            return True

        success = True
        for notifier in self.notifiers:
            try:
                res = notifier.send_digest(ranked_matches)
                if not res:
                    success = False
            except Exception as e:
                logger.error("Notifier error in %s: %s", notifier.__class__.__name__, str(e))
                success = False

        return success

    def send_notification(self, title: str, message: str, subtitle: Optional[str] = None) -> bool:
        """Sends arbitrary alert notification across all channels."""
        if not self.enabled:
            return True

        success = True
        for notifier in self.notifiers:
            if hasattr(notifier, "send_notification"):
                try:
                    res = notifier.send_notification(title, message, subtitle)
                    if not res:
                        success = False
                except Exception as e:
                    logger.error("Notifier error in %s: %s", notifier.__class__.__name__, str(e))
                    success = False
        return success
