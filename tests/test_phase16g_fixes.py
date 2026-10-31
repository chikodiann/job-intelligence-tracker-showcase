"""Unit and integration tests for Phase 16G — Dashboard Data-to-UI Flow & JavaScript Validation."""

import re
import subprocess
import sys
import pytest

from job_monitor.dashboard.ui import get_dashboard_html


def test_escape_html_helper_defined_in_javascript():
    """Requirement 2: Verifies escapeHtml() is defined inside the generated dashboard JavaScript block."""
    html = get_dashboard_html()
    match = re.search(r"<script>(.*?)</script>", html, re.DOTALL)
    assert match is not None, "HTML dashboard template must contain a <script> block"

    js_code = match.group(1)

    # Must find an explicit function definition for escapeHtml in JS
    pattern = r"function\s+escapeHtml\s*\(\s*str\s*\)"
    assert re.search(pattern, js_code) is not None, "escapeHtml helper function MUST be defined inside the <script> block"


def test_js_execution_of_card_rendering_and_escape_html():
    """Requirement 3: Executes JavaScript card rendering in JavaScript runtime and verifies escapeHtml escaping."""
    html = get_dashboard_html()
    match = re.search(r"<script>(.*?)</script>", html, re.DOTALL)
    assert match is not None

    js_code = match.group(1)

    if sys.platform != "darwin":
        pytest.skip("JS execution test requires macOS JavaScript OSA runtime")

    # Construct test script that initializes stubs and executes createJobCardHtml and escapeHtml
    test_harness = """
    function document_stub() { return { classList: { add: function(){}, remove: function(){} }, style: {}, textContent: '', innerHTML: '', value: '' }; }
    var window = { location: { href: '' } };
    var document = { getElementById: function(){ return document_stub(); }, createElement: function(){ return document_stub(); } };
    var setInterval = function(){};
    var clearInterval = function(){};
    var fetch = function(){ return Promise.resolve({ ok: true, json: function(){ return Promise.resolve({}); } }); };
    
    // Inject the dashboard JS
    """ + js_code + """
    
    // Test 1: escapeHtml character replacement
    var escaped = escapeHtml("AT&T <Script> 'Quote' & \\"Double\\"");
    if (escaped !== "AT&amp;T &lt;Script&gt; &#39;Quote&#39; &amp; &quot;Double&quot;") {
        throw new Error("escapeHtml did not escape correctly: " + escaped);
    }
    
    // Test 2: Execute createJobCardHtml without ReferenceError
    var mockRecord = {
        job: {
            id: "job-101",
            title: "Senior AI & ML Specialist <Test>",
            company_name: "Acme Corp & Co",
            source_name: "remotive",
            url: "https://example.com/job",
            review_state: "UNREVIEWED",
            status: "OPEN"
        },
        explanation: {
            remote_eligibility: "ELIGIBLE",
            priority_score: 95,
            technical_match_score: 88,
            freshness_factor: 1.0,
            compensation_text: "$120,000 & bonus",
            why_match: "High technical & domain match",
            location_requirement: "Remote Worldwide"
        }
    };
    
    var cardHtml = createJobCardHtml(mockRecord);
    if (!cardHtml || cardHtml.indexOf("&amp;") === -1) {
        throw new Error("createJobCardHtml output missing expected escaped HTML: " + cardHtml);
    }
    """

    res = subprocess.run(["osascript", "-l", "JavaScript", "-e", test_harness], capture_output=True, text=True)
    assert res.returncode == 0, f"JavaScript runtime error during card rendering test:\n{res.stderr}"


def test_dashboard_error_handling_retry_ui():
    """Requirement 4: Verifies UI script contains error state rendering and retry capabilities."""
    html = get_dashboard_html()
    match = re.search(r"<script>(.*?)</script>", html, re.DOTALL)
    assert match is not None
    js_code = match.group(1)

    assert "Failed to load dashboard data" in js_code
    assert "Retry" in js_code
    assert "loadDashboardData()" in js_code
