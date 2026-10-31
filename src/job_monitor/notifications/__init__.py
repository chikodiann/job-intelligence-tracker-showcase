import sys
from typing import Optional
from .composite import CompositeNotifier
from .desktop_macos import MacOSDesktopNotifier
from .desktop_windows import WindowsDesktopNotifier


def get_platform_notifier(target_platform: Optional[str] = None) -> CompositeNotifier:
    """Returns platform-specific desktop notifier composite."""
    import sys
    plat = (target_platform or sys.platform).lower()
    if plat.startswith("win") or plat == "win32":
        notifiers = [WindowsDesktopNotifier()]
    elif plat == "darwin" or "mac" in plat:
        notifiers = [MacOSDesktopNotifier()]
    else:
        notifiers = []
    return CompositeNotifier(enabled=True, notifiers=notifiers)


__all__ = ["MacOSDesktopNotifier", "WindowsDesktopNotifier", "CompositeNotifier", "get_platform_notifier"]

