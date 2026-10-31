"""Unit tests for Phase 16C — PyInstaller Entrypoint and Info.plist Configuration."""

from pathlib import Path
import pytest
from job_monitor.cli import main as cli_main


def test_entrypoint_file_exists_and_imports_cli():
    """Verifies that src/entrypoint.py exists and imports job_monitor.cli.main."""
    project_root = Path(__file__).resolve().parent.parent
    entrypoint_path = project_root / "src" / "entrypoint.py"

    assert entrypoint_path.exists(), "src/entrypoint.py entrypoint script missing!"
    content = entrypoint_path.read_text(encoding="utf-8")
    assert "from job_monitor.cli import main" in content
    assert callable(cli_main)


def test_spec_uses_entrypoint_and_lsbackgroundonly_false():
    """Verifies job_monitor.spec uses src/entrypoint.py and sets LSBackgroundOnly to False."""
    project_root = Path(__file__).resolve().parent.parent
    spec_path = project_root / "job_monitor.spec"

    assert spec_path.exists(), "job_monitor.spec missing!"
    content = spec_path.read_text(encoding="utf-8")

    assert "['src/entrypoint.py']" in content, "job_monitor.spec must use src/entrypoint.py as main Analysis script"
    assert "'LSBackgroundOnly': False" in content, "job_monitor.spec BUNDLE must set LSBackgroundOnly to False"
