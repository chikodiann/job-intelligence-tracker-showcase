"""Regression tests for time-zone initialization and tzdata dependency packaging."""

from datetime import datetime, timezone, timedelta
import importlib
from pathlib import Path
from unittest.mock import patch
import zoneinfo
import pytest

import job_monitor.utils.timezone as tz_utils
from job_monitor.utils.timezone import (
    LAGOS_TZ,
    get_lagos_date_str,
    get_lagos_now,
    get_local_date_str,
    get_local_now,
)


def test_pyproject_dependency_declared():
    """Verifies that tzdata is declared as a project runtime dependency in pyproject.toml."""
    pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
    content = pyproject_path.read_text(encoding="utf-8")
    assert "tzdata>=" in content, "tzdata runtime dependency missing from pyproject.toml"


def test_pyinstaller_spec_includes_tzdata():
    """Verifies job_monitor.spec collects tzdata data files and includes tzdata hiddenimport."""
    spec_path = Path(__file__).resolve().parent.parent / "job_monitor.spec"
    content = spec_path.read_text(encoding="utf-8")
    assert "collect_data_files('tzdata')" in content or 'collect_data_files("tzdata")' in content, (
        "collect_data_files('tzdata') missing from job_monitor.spec"
    )
    assert "'tzdata'" in content or '"tzdata"' in content, "tzdata hiddenimport missing from job_monitor.spec"
    assert "'zoneinfo'" in content or '"zoneinfo"' in content, "zoneinfo hiddenimport missing from job_monitor.spec"


def test_zoneinfo_lagos_resolution():
    """Verifies ZoneInfo('Africa/Lagos') resolves as a ZoneInfo instance with +01:00 UTC offset."""
    assert isinstance(LAGOS_TZ, zoneinfo.ZoneInfo), "LAGOS_TZ is not a zoneinfo.ZoneInfo instance"
    assert getattr(LAGOS_TZ, "key", None) == "Africa/Lagos", f"LAGOS_TZ key is {getattr(LAGOS_TZ, 'key', None)}"
    dt_utc = datetime(2026, 10, 8, 12, 0, tzinfo=timezone.utc)
    dt_lagos = dt_utc.astimezone(LAGOS_TZ)
    assert dt_lagos.utcoffset() == timedelta(hours=1)
    assert dt_lagos.hour == 13


def test_lagos_date_str_boundary_utc():
    """Verifies date calculation around UTC midnight boundary for Africa/Lagos (UTC+1)."""
    # 23:30 UTC on Oct 8 is 00:30 WAT on Oct 9
    dt_late_utc = datetime(2026, 10, 8, 23, 30, tzinfo=timezone.utc)
    date_str = get_lagos_date_str(dt_late_utc)
    assert date_str == "2026-10-09"

    # Naive datetime assume UTC
    dt_naive = datetime(2026, 10, 8, 23, 30)
    assert get_lagos_date_str(dt_naive) == "2026-10-09"


def test_timezone_module_fallback_when_zoneinfo_not_found():
    """Verifies timezone module initialization fallback when ZoneInfo raises ZoneInfoNotFoundError."""

    def mock_zoneinfo_side_effect(key):
        if key == "Africa/Lagos":
            raise zoneinfo.ZoneInfoNotFoundError("No time zone found with key Africa/Lagos")
        return zoneinfo.ZoneInfo(key)

    with patch("job_monitor.utils.timezone.ZoneInfo", side_effect=mock_zoneinfo_side_effect):
        # Reload timezone module under mock
        reloaded_tz = importlib.reload(tz_utils)
        try:
            assert reloaded_tz.LAGOS_TZ.utcoffset(datetime.now()) == timedelta(hours=1)
            dt_late_utc = datetime(2026, 10, 8, 23, 30, tzinfo=timezone.utc)
            assert reloaded_tz.get_lagos_date_str(dt_late_utc) == "2026-10-09"
        finally:
            # Restore module state
            importlib.reload(tz_utils)
