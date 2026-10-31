from datetime import datetime, timezone
import pytest
from job_monitor.config import load_config
from job_monitor.db.storage import JobStorage
from job_monitor.ingestion import IngestionPipeline
from job_monitor.interfaces.fetcher import BaseJobFetcher
from job_monitor.interfaces.notifier import BaseNotifier
from job_monitor.models import NormalizedJob, RawJob, EmploymentType, SalaryPeriod
from job_monitor.notifications import CompositeNotifier, MacOSDesktopNotifier
from job_monitor.pipeline_runner import OperationalPipelineRunner
from job_monitor.reports import DailyReportGenerator, ReportHistoryStore
from job_monitor.scoring import JobQueryService, JobScorer, RemoteEligibility, RoleRelevance, EligibilityClassifier


class FailingFetcher(BaseJobFetcher):
    def __init__(self):
        super().__init__(source_name="failing_source", rate_limit_delay_seconds=0.0)

    def fetch_jobs(self, limit=None):
        raise ConnectionError("Vendor API network timeout")


class SingleJobFetcher(BaseJobFetcher):
    def __init__(self, source_name="single_source", ext_id="j1", title="Backend Engineer", company="TechCorp"):
        super().__init__(source_name=source_name, rate_limit_delay_seconds=0.0)
        self.ext_id = ext_id
        self.title = title
        self.company = company

    def fetch_jobs(self, limit=None):
        return [
            RawJob(
                source_name=self.source_name,
                external_id=self.ext_id,
                payload={
                    "id": self.ext_id,
                    "title": self.title,
                    "company_name": self.company,
                    "url": f"https://example.com/job/{self.ext_id}",
                    "publication_date": "2026-10-07T08:00:00Z",
                    "candidate_required_location": "Worldwide",
                    "description": "<p>Java Spring Boot REST API PostgreSQL</p>"
                }
            )
        ]


# 1-9. Geographic eligibility tests
def test_geographic_eligibility_cases():
    # 1. USA-only => INELIGIBLE
    elig1, _ = EligibilityClassifier.classify("USA")
    assert elig1 == RemoteEligibility.INELIGIBLE

    elig2, _ = EligibilityClassifier.classify("Remote (US Only)")
    assert elig2 == RemoteEligibility.INELIGIBLE

    # 2. Canada-only => INELIGIBLE
    elig3, _ = EligibilityClassifier.classify("Canada Only")
    assert elig3 == RemoteEligibility.INELIGIBLE

    # 3. UK-only => INELIGIBLE
    elig4, _ = EligibilityClassifier.classify("UK Only")
    assert elig4 == RemoteEligibility.INELIGIBLE

    # 4. EU-only => INELIGIBLE
    elig5, _ = EligibilityClassifier.classify("EU Only")
    assert elig5 == RemoteEligibility.INELIGIBLE

    # 5. Americas-only => INELIGIBLE (e.g. Americas, Europe, Israel)
    elig6, _ = EligibilityClassifier.classify("Americas, Europe, Israel")
    assert elig6 == RemoteEligibility.INELIGIBLE

    # 6. Worldwide => ELIGIBLE
    elig7, _ = EligibilityClassifier.classify("Worldwide")
    assert elig7 == RemoteEligibility.ELIGIBLE

    # 7. EMEA => ELIGIBLE
    elig8, _ = EligibilityClassifier.classify("EMEA")
    assert elig8 == RemoteEligibility.ELIGIBLE

    # 8. Nigeria => ELIGIBLE
    elig9, _ = EligibilityClassifier.classify("Nigeria")
    assert elig9 == RemoteEligibility.ELIGIBLE

    # 9. Unknown geography => UNKNOWN
    elig10, _ = EligibilityClassifier.classify("Remote")
    assert elig10 == RemoteEligibility.UNKNOWN


# 10. INELIGIBLE never enters ranking views
def test_ineligible_never_enters_ranking_views():
    storage = JobStorage(db_path=":memory:")
    qs = JobQueryService(storage=storage)

    job_usa = NormalizedJob(
        source_name="remotive",
        external_id="u1",
        url="https://example.com/u1",
        title="Principal Solutions Architect",
        company_name="Tenable",
        location_requirement="USA",
        content_hash="h_u1",
        canonical_fingerprint="fp_u1",
        description_text="Java Spring REST APIs microservices"
    )
    storage.save_normalized_job(job_usa)

    assert len(qs.get_apply_first_jobs()) == 0
    assert len(qs.get_fastest_cash_jobs()) == 0
    assert len(qs.get_best_technical_matches()) == 0
    assert len(qs.get_best_long_term_jobs()) == 0


# 11. UNKNOWN never enters APPLY_FIRST
def test_unknown_never_enters_apply_first():
    storage = JobStorage(db_path=":memory:")
    qs = JobQueryService(storage=storage)

    job_unknown = NormalizedJob(
        source_name="remotive",
        external_id="unk1",
        url="https://example.com/unk1",
        title="Java Backend Engineer",
        company_name="MysteryCo",
        location_requirement="Remote",
        content_hash="h_unk1",
        canonical_fingerprint="fp_unk1",
        description_text="Java Spring Boot REST API"
    )
    storage.save_normalized_job(job_unknown)

    apply_first = qs.get_apply_first_jobs()
    assert len(apply_first) == 0  # UNKNOWN is excluded from APPLY_FIRST!


# 12. $170/hr INELIGIBLE never enters FAST_CASH
def test_high_pay_ineligible_never_enters_fast_cash():
    storage = JobStorage(db_path=":memory:")
    qs = JobQueryService(storage=storage)

    job_170_inelig = NormalizedJob(
        source_name="remotive",
        external_id="fc170",
        url="https://example.com/fc170",
        title="Senior AI Engineer",
        company_name="USCorp",
        location_requirement="USA Only",
        salary_min=170.0,
        salary_max=170.0,
        salary_period=SalaryPeriod.HOURLY,
        employment_type=EmploymentType.CONTRACT,
        content_hash="h_170",
        canonical_fingerprint="fp_170",
        description_text="Contract AI engineering role in the US"
    )
    storage.save_normalized_job(job_170_inelig)

    fast_cash = qs.get_fastest_cash_jobs()
    assert len(fast_cash) == 0  # $170/hr INELIGIBLE excluded!


# 13. Low technical score cannot produce "Strong match"
def test_low_tech_score_cannot_produce_strong_match():
    scorer = JobScorer()
    job_trainer = NormalizedJob(
        source_name="jobicy",
        external_id="tr1",
        url="https://example.com/tr1",
        title="AI Code Trainer",
        company_name="TrainerCo",
        location_requirement="Worldwide",
        content_hash="h_tr1",
        canonical_fingerprint="fp_tr1",
        description_text="Evaluate basic code responses and prompt engineering"
    )
    exp = scorer.evaluate_job(job_trainer)
    assert "Strong match" not in exp.why_match  # Must never call non-Java/Spring role a "Strong match"!



# 14. Actual job requirements drive POTENTIAL GAP
def test_actual_requirements_drive_gap():
    scorer = JobScorer()
    job_go = NormalizedJob(
        source_name="remotive",
        external_id="go1",
        url="https://example.com/go1",
        title="Golang Backend Engineer",
        company_name="GoCorp",
        location_requirement="Worldwide",
        content_hash="h_go1",
        canonical_fingerprint="fp_go1",
        description_text="Build high throughput backend services using Go and microservices"
    )
    exp = scorer.evaluate_job(job_go)
    assert "Primary gap: Go is not one of Ann's strongest production languages" in exp.potential_gap


# 15, 16, 17. NEW != UPDATED != UNCHANGED
def test_new_updated_unchanged_counts():
    storage = JobStorage(db_path=":memory:")
    fetcher = SingleJobFetcher()
    pipeline = IngestionPipeline(storage=storage, fetchers=[fetcher])

    summary1 = pipeline.run()
    assert summary1.total_new == 1
    assert summary1.total_updated == 0
    assert summary1.total_duplicates == 0

    summary2 = pipeline.run()
    assert summary2.total_new == 0
    assert summary2.total_updated == 0
    assert summary2.total_duplicates == 1  # Unchanged job counted as duplicate/unchanged, NOT new!


# Source failure isolation test
def test_source_failure_isolation():
    storage = JobStorage(db_path=":memory:")
    pipeline = IngestionPipeline(
        storage=storage,
        fetchers=[FailingFetcher(), SingleJobFetcher()]
    )
    summary = pipeline.run()
    assert summary.total_fetched == 1
    assert summary.sources["failing_source"].failed == 1
    assert summary.sources["single_source"].fetched == 1


# Report generation & Empty-result handling
def test_report_generation_empty():
    storage = JobStorage(db_path=":memory:")
    qs = JobQueryService(storage=storage)
    gen = DailyReportGenerator(query_service=qs)

    report = gen.generate_report()
    assert "ANN'S DAILY REMOTE JOB INTELLIGENCE" in report
    assert "APPLY FIRST" in report
    assert "No opportunities matched" in report  # Empty result handled gracefully


# Notification abstraction & Disabled flag
def test_notifications():
    class TestNotifier(BaseNotifier):
        def __init__(self):
            self.sent = False
        def send_digest(self, matches):
            self.sent = True
            return True

    mock_n = TestNotifier()
    comp = CompositeNotifier(enabled=True, notifiers=[mock_n])
    comp.send_digest([])
    assert mock_n.sent is True

    # Disabled check
    mock_n2 = TestNotifier()
    comp_disabled = CompositeNotifier(enabled=False, notifiers=[mock_n2])
    comp_disabled.send_digest([])
    assert mock_n2.sent is False


# NON_TARGET_ROLE never appearing in primary views
def test_non_target_never_appears():
    storage = JobStorage(db_path=":memory:")
    qs = JobQueryService(storage=storage)

    job_sales = NormalizedJob(
        source_name="remotive",
        external_id="s1",
        url="https://example.com/s1",
        title="Sales Development Representative",
        company_name="SalesCorp",
        content_hash="h1",
        canonical_fingerprint="fp1",
        description_text="Cold outreach sales"
    )
    storage.save_normalized_job(job_sales)

    apply_first = qs.get_apply_first_jobs()
    fast_cash = qs.get_fastest_cash_jobs()
    tech_match = qs.get_best_technical_matches()

    assert len(apply_first) == 0
    assert len(fast_cash) == 0
    assert len(tech_match) == 0


# Frontend-first roles penalized
def test_frontend_first_penalized():
    storage = JobStorage(db_path=":memory:")
    qs = JobQueryService(storage=storage)

    backend = NormalizedJob(
        source_name="remotive",
        external_id="b1",
        url="https://example.com/b1",
        title="Backend Software Engineer",
        company_name="TechCo",
        location_requirement="Worldwide",
        content_hash="h_b1",
        canonical_fingerprint="fp_b1",
        description_text="Build Java REST APIs and microservices"
    )
    frontend = NormalizedJob(
        source_name="remotive",
        external_id="f1",
        url="https://example.com/f1",
        title="Frontend Engineer",
        company_name="TechCo",
        location_requirement="Worldwide",
        content_hash="h_f1",
        canonical_fingerprint="fp_f1",
        description_text="Build React and CSS UI with Java backend APIs"
    )

    storage.save_normalized_job(backend)
    storage.save_normalized_job(frontend)

    tech_matches = qs.get_best_technical_matches()
    assert len(tech_matches) == 2
    assert tech_matches[0].job.external_id == "b1"  # Backend outranks Frontend!

