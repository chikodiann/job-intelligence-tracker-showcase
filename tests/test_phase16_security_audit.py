"""Unit tests for Phase 16B — Pre-Build Security Audit & Tester Profile Isolation."""

import pytest
from pathlib import Path
from job_monitor.beta.security_audit import PreBuildSecurityAudit, SecurityAuditError, perform_pre_build_security_audit


def test_audit_passes_on_clean_staging(tmp_path):
    """Verifies that pre-build security audit passes cleanly when staging contains only embedded_profile.yaml."""
    ws = tmp_path / "workspace"
    staging = tmp_path / "staging"
    ws.mkdir()
    staging.mkdir()

    # Create valid embedded_profile.yaml
    embedded = staging / "embedded_profile.yaml"
    embedded.write_text("id: oghor\nname: Oghor\nprofessional_title: Cloud Engineer\n", encoding="utf-8")

    config = staging / "config.yaml"
    config.write_text("app:\n  name: Test App\n", encoding="utf-8")

    assert perform_pre_build_security_audit(workspace_dir=ws, staging_dir=staging, target_profile_id="oghor") is True


def test_audit_passes_on_internal_embedded_profile(tmp_path):
    """Verifies pre-build security audit passes when embedded_profile.yaml is located in PyInstaller 6+ _internal/ folder."""
    ws = tmp_path / "workspace"
    staging = tmp_path / "staging"
    internal = staging / "_internal"
    ws.mkdir()
    internal.mkdir(parents=True)

    # Create valid embedded_profile.yaml in _internal/
    embedded = internal / "embedded_profile.yaml"
    embedded.write_text("id: oghor\nname: Oghor\nprofessional_title: Cloud Engineer\n", encoding="utf-8")

    assert perform_pre_build_security_audit(workspace_dir=ws, staging_dir=staging, target_profile_id="oghor") is True


def test_audit_fails_on_jobs_db(tmp_path):
    """Verifies that pre-build security audit fails if jobs.db is found in staging."""
    ws = tmp_path / "workspace"
    staging = tmp_path / "staging"
    ws.mkdir()
    staging.mkdir()

    embedded = staging / "embedded_profile.yaml"
    embedded.write_text("id: oghor\nname: Oghor\n", encoding="utf-8")

    db = staging / "jobs.db"
    db.write_text("fake sqlite content", encoding="utf-8")

    with pytest.raises(SecurityAuditError) as exc_info:
        perform_pre_build_security_audit(workspace_dir=ws, staging_dir=staging, target_profile_id="oghor")
    assert "Prohibited SQLite database file found in staging" in str(exc_info.value)


def test_audit_fails_on_env_file(tmp_path):
    """Verifies that pre-build security audit fails if .env file is found in staging."""
    ws = tmp_path / "workspace"
    staging = tmp_path / "staging"
    ws.mkdir()
    staging.mkdir()

    embedded = staging / "embedded_profile.yaml"
    embedded.write_text("id: oghor\nname: Oghor\n", encoding="utf-8")

    env_file = staging / ".env"
    env_file.write_text("SECRET_KEY=12345", encoding="utf-8")

    with pytest.raises(SecurityAuditError) as exc_info:
        perform_pre_build_security_audit(workspace_dir=ws, staging_dir=staging, target_profile_id="oghor")
    assert "Prohibited environment configuration file found in staging" in str(exc_info.value)


def test_audit_fails_on_multiple_profiles(tmp_path):
    """Verifies that pre-build security audit fails if multiple candidate profiles are staged."""
    ws = tmp_path / "workspace"
    staging = tmp_path / "staging"
    ws.mkdir()
    staging.mkdir()

    embedded = staging / "embedded_profile.yaml"
    embedded.write_text("id: oghor\nname: Oghor\n", encoding="utf-8")

    profiles_dir = staging / "profiles"
    profiles_dir.mkdir()
    (profiles_dir / "oghor.yaml").write_text("id: oghor\n", encoding="utf-8")
    (profiles_dir / "ann.yaml").write_text("id: ann\n", encoding="utf-8")

    with pytest.raises(SecurityAuditError) as exc_info:
        perform_pre_build_security_audit(workspace_dir=ws, staging_dir=staging, target_profile_id="oghor")
    assert "Multiple candidate profiles found in build staging" in str(exc_info.value)


def test_audit_fails_on_cv_files(tmp_path):
    """Verifies that pre-build security audit fails if candidate CV files are found in staging."""
    ws = tmp_path / "workspace"
    staging = tmp_path / "staging"
    ws.mkdir()
    staging.mkdir()

    embedded = staging / "embedded_profile.yaml"
    embedded.write_text("id: oghor\nname: Oghor\n", encoding="utf-8")

    cv_file = staging / "Oghor_CV.pdf"
    cv_file.write_bytes(b"%PDF-1.4 binary content")

    with pytest.raises(SecurityAuditError) as exc_info:
        perform_pre_build_security_audit(workspace_dir=ws, staging_dir=staging, target_profile_id="oghor")
    assert "Prohibited CV / document file found in staging" in str(exc_info.value)


def test_windows_zip_packaging(tmp_path, monkeypatch):
    """Verifies that package_windows_zip creates a valid ZIP archive with START_HERE_BETA_TESTER.txt."""
    import sys
    import zipfile
    from pathlib import Path

    proj_root = Path(__file__).resolve().parent.parent
    if str(proj_root) not in sys.path:
        sys.path.insert(0, str(proj_root))

    from scripts.package_windows_zip import package_windows_zip
    import scripts.package_windows_zip as pkg_mod

    # Setup mock workspace and dist directory
    ws = tmp_path / "project_root"
    dist = ws / "dist"
    target_app = dist / "AnnsJobTracker_Tester_Windows"
    target_app.mkdir(parents=True)

    (target_app / "embedded_profile.yaml").write_text("id: tester\nname: Tester\n", encoding="utf-8")
    (target_app / "AnnsJobTracker.exe").write_bytes(b"MZfake_exe_content")

    monkeypatch.setattr(pkg_mod, "PROJECT_ROOT", ws)

    zip_path = package_windows_zip(profile_id="tester")

    assert zip_path.exists()
    assert zip_path.name == "AnnsJobTracker_Tester_Windows.zip"

    # Verify ZIP contents
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        assert "AnnsJobTracker_Tester_Windows/START_HERE_BETA_TESTER.txt" in names
        assert "AnnsJobTracker_Tester_Windows/AnnsJobTracker.exe" in names
        assert "AnnsJobTracker_Tester_Windows/embedded_profile.yaml" in names

        readme_bytes = zf.read("AnnsJobTracker_Tester_Windows/START_HERE_BETA_TESTER.txt")
        assert b"ANN'S JOB INTELLIGENCE & APPLICATION TRACKER" in readme_bytes
        assert b"AnnsJobTracker.exe" in readme_bytes

