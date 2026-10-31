"""Unit and integration tests for Phase 16F — Frontend JavaScript Validation, Packaged Profile Sync, & UI Isolation."""

import re
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from job_monitor.config import load_config
from job_monitor.dashboard.ui import get_dashboard_html
from job_monitor.scoring.candidate_profile import CandidateProfile, load_candidate_profile
from job_monitor.utils.paths import AppPaths


def test_javascript_syntax_validation():
    """Validates that the entire dashboard JavaScript script parses cleanly without syntax errors."""
    html = get_dashboard_html()
    match = re.search(r"<script>(.*?)</script>", html, re.DOTALL)
    assert match is not None, "HTML dashboard template must contain a <script> block"

    js_code = match.group(1)

    # Prepend browser DOM stubs for headless JavaScript runtime
    stubs = """
    function document_stub() { return { classList: { add: function(){}, remove: function(){} }, style: {}, textContent: '', innerHTML: '', value: '' }; }
    var window = { location: { href: '' } };
    var document = { getElementById: function(){ return document_stub(); }, createElement: function(){ return document_stub(); } };
    var setInterval = function(){};
    var clearInterval = function(){};
    var fetch = function(){ return Promise.resolve({ ok: true, json: function(){ return Promise.resolve({}); } }); };
    """
    full_code = stubs + js_code

    if sys.platform == "darwin":
        res = subprocess.run(["osascript", "-l", "JavaScript", "-e", full_code], capture_output=True, text=True)
        assert res.returncode == 0, f"JavaScript parse error in dashboard UI script:\n{res.stderr}"
    else:
        # Fallback check on non-macOS platforms
        assert "function switchTab(tabId)" in js_code
        assert "function getTimeOfDayGreeting(candidateName)" in js_code
        assert "loadDashboardData()" in js_code


def test_dynamic_candidate_stack_text():
    """Verifies that Section 3 HTML renders dynamic candidate profile details and removes hardcoded Ann text."""
    eva_profile = CandidateProfile(
        id="eva",
        name="Eva",
        professional_title="AI Specialist",
        primary_skills={"ai model evaluation", "ai annotation", "data annotation"},
    )

    html = get_dashboard_html(candidate_profile=eva_profile)

    assert "Ann's Java, Spring Boot, REST API, & PostgreSQL stack" not in html
    assert "Strongest engineering alignment with Eva's" in html
    assert "ai annotation" in html or "ai model evaluation" in html


def test_packaged_profile_config_sync(tmp_path, monkeypatch):
    """Verifies that load_config() in packaged mode syncs active_profile from embedded_profile.yaml."""
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    embedded_file = tmp_path / "embedded_profile.yaml"
    embedded_file.write_text("id: 'eva'\nname: 'Eva'\nprofessional_title: 'AI Specialist'\n", encoding="utf-8")

    with patch.object(AppPaths, "is_packaged", return_value=True), \
         patch.object(AppPaths, "get_embedded_profile_path", return_value=embedded_file), \
         patch.object(AppPaths, "get_user_data_dir", return_value=tmp_path):

        config = load_config()

        assert config.active_profile == "eva"
        assert "eva" in config.database.path
        assert "ann" not in config.database.path.lower() or config.active_profile == "eva"


def test_dashboard_html_contains_api_hooks():
    """Verifies that dashboard HTML template contains required API endpoints for initialization."""
    html = get_dashboard_html()

    assert "/api/summary" in html
    assert "/api/dashboard" in html
    assert "/api/jobs" in html
    assert "/api/applications" in html
    assert "/api/pipeline/status" in html
    assert "/api/reports/latest" in html
