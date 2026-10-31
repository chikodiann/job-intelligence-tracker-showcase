from datetime import datetime
from job_monitor.ingestion.parsers import HTMLSanitizer, DateParser, SalaryParser
from job_monitor.models.normalized_job import SalaryPeriod


def test_html_sanitizer():
    raw_html = "<div><h1>Job Title</h1><p>We are looking for a <b>Python</b> dev.</p><br>Line 2 &amp; more.</div>"
    clean = HTMLSanitizer.sanitize(raw_html)
    assert "Job Title" in clean
    assert "Python" in clean
    assert "&amp;" not in clean
    assert "Line 2 & more." in clean
    assert "<h1>" not in clean


def test_date_parser():
    # ISO 8601
    dt1 = DateParser.parse_date("2026-10-07T08:00:00Z")
    assert dt1 is not None
    assert dt1.year == 2026
    assert dt1.month == 10
    assert dt1.day == 7

    # RFC 822 / 2822 RSS date
    dt2 = DateParser.parse_date("Wed, 07 Oct 2026 08:00:00 +0000")
    assert dt2 is not None
    assert dt2.year == 2026

    # Invalid date
    assert DateParser.parse_date("invalid-date") is None
    assert DateParser.parse_date(None) is None


def test_salary_parser_annual():
    min_val, max_val, curr, period, ann_min, ann_max = SalaryParser.parse_salary("$120,000 - $150,000")
    assert min_val == 120000.0
    assert max_val == 150000.0
    assert curr == "USD"
    assert period == SalaryPeriod.ANNUAL
    assert ann_min == 120000.0
    assert ann_max == 150000.0


def test_salary_parser_hourly():
    min_val, max_val, curr, period, ann_min, ann_max = SalaryParser.parse_salary("$30 - $40/hour")
    assert min_val == 30.0
    assert max_val == 40.0
    assert curr == "USD"
    assert period == SalaryPeriod.HOURLY
    assert ann_min == 30.0 * 2080
    assert ann_max == 40.0 * 2080


def test_salary_parser_low_and_undisclosed():
    # Low salary test (No floor policy - must parse correctly)
    min_val, max_val, curr, period, ann_min, ann_max = SalaryParser.parse_salary("$15 - $20/hour")
    assert min_val == 15.0
    assert max_val == 20.0
    assert ann_min == 15.0 * 2080

    # Undisclosed / missing salary
    min_val, max_val, curr, period, ann_min, ann_max = SalaryParser.parse_salary("Competitive")
    assert min_val is None
    assert max_val is None
    assert curr is None
    assert period == SalaryPeriod.UNKNOWN
