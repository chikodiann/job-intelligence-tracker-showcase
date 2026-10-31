from datetime import datetime, timezone
import pytest
from job_monitor.db.storage import JobStorage
from job_monitor.models import NormalizedJob, EmploymentType, SalaryPeriod
from job_monitor.scoring import (
    JobScorer,
    JobQueryService,
    RemoteEligibility,
    RoleRelevance,
    JobCategoryTag,
)


def create_sample_job(
    title: str,
    company: str,
    location: str,
    emp_type: EmploymentType,
    salary_min: float = None,
    salary_max: float = None,
    salary_period: SalaryPeriod = SalaryPeriod.UNKNOWN,
    desc: str = "",
    source_name: str = "remotive",
    ext_id: str = "1",
) -> NormalizedJob:
    now = datetime.now(timezone.utc)
    return NormalizedJob(
        source_name=source_name,
        external_id=ext_id,
        url=f"https://example.com/job/{ext_id}",
        title=title,
        company_name=company,
        location_requirement=location,
        employment_type=emp_type,
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency="USD" if salary_min else None,
        salary_period=salary_period,
        annualized_min_usd=(salary_min * 2080 if salary_period == SalaryPeriod.HOURLY else salary_min) if salary_min else None,
        annualized_max_usd=(salary_max * 2080 if salary_period == SalaryPeriod.HOURLY else salary_max) if salary_max else None,
        description_raw=desc,
        description_text=desc,
        content_hash=f"hash_{ext_id}",
        canonical_fingerprint=f"fp_{ext_id}",
        posted_at=now,
        fetched_at=now,
    )


# --- SECTION 14 FALSE-POSITIVE TEST CASES (1 to 8) ---

def test_fp_1_renewals_manager():
    job = create_sample_job("Associate Renewals Manager", "GitLab", "Worldwide", EmploymentType.FULL_TIME, 50000, 100000, SalaryPeriod.ANNUAL, "Manage client renewals.", ext_id="fp1")
    exp = JobScorer().evaluate_job(job)
    assert exp.role_relevance == RoleRelevance.NON_TARGET_ROLE
    assert exp.technical_match_score == 0.0
    assert exp.priority_score == 0.0

def test_fp_2_customer_success_manager():
    job = create_sample_job("Customer Success Manager", "SaaS Co", "Worldwide", EmploymentType.FULL_TIME, 80000, 100000, SalaryPeriod.ANNUAL, "Help SaaS customers succeed.", ext_id="fp2")
    exp = JobScorer().evaluate_job(job)
    assert exp.role_relevance == RoleRelevance.NON_TARGET_ROLE
    assert exp.technical_match_score == 0.0
    assert exp.priority_score == 0.0

def test_fp_3_hospitality_role():
    job = create_sample_job("Creative Hospitality Lead", "Galileo", "Worldwide", EmploymentType.CONTRACT, 50, 50, SalaryPeriod.HOURLY, "Hospitality services.", ext_id="fp3")
    exp = JobScorer().evaluate_job(job)
    assert exp.role_relevance == RoleRelevance.NON_TARGET_ROLE
    assert exp.technical_match_score == 0.0
    assert exp.priority_score == 0.0

def test_fp_4_nurse_practitioner():
    job = create_sample_job("Nurse Practitioner (Remote)", "Galileo", "Worldwide", EmploymentType.CONTRACT, 50, 50, SalaryPeriod.HOURLY, "Clinical nursing duties.", ext_id="fp4")
    exp = JobScorer().evaluate_job(job)
    assert exp.role_relevance == RoleRelevance.NON_TARGET_ROLE
    assert exp.technical_match_score == 0.0
    assert exp.priority_score == 0.0

def test_fp_5_sales_representative():
    job = create_sample_job("Sales Development Representative", "SalesCorp", "Worldwide", EmploymentType.FULL_TIME, 60000, 80000, SalaryPeriod.ANNUAL, "Cold calls and leads.", ext_id="fp5")
    exp = JobScorer().evaluate_job(job)
    assert exp.role_relevance == RoleRelevance.NON_TARGET_ROLE
    assert exp.technical_match_score == 0.0
    assert exp.priority_score == 0.0

def test_fp_6_privacy_analyst():
    job = create_sample_job("Analyst, Privacy", "Coinbase", "Worldwide", EmploymentType.FULL_TIME, 90000, 120000, SalaryPeriod.ANNUAL, "GDPR compliance analysis.", ext_id="fp6")
    exp = JobScorer().evaluate_job(job)
    assert exp.role_relevance == RoleRelevance.NON_TARGET_ROLE
    assert exp.technical_match_score == 0.0
    assert exp.priority_score == 0.0

def test_fp_7_construction_project_manager():
    job = create_sample_job("Construction Project Manager", "BuildInc", "Worldwide", EmploymentType.FULL_TIME, 80000, 100000, SalaryPeriod.ANNUAL, "Site building management.", ext_id="fp7")
    exp = JobScorer().evaluate_job(job)
    assert exp.role_relevance == RoleRelevance.NON_TARGET_ROLE
    assert exp.technical_match_score == 0.0
    assert exp.priority_score == 0.0

def test_fp_8_generic_content_writer():
    job = create_sample_job("Generic Content Writer", "MediaAgency", "Worldwide", EmploymentType.CONTRACT, 25, 25, SalaryPeriod.HOURLY, "Write blog articles.", ext_id="fp8")
    exp = JobScorer().evaluate_job(job)
    assert exp.role_relevance == RoleRelevance.NON_TARGET_ROLE
    assert exp.technical_match_score == 0.0
    assert exp.priority_score == 0.0


# --- SECTION 14 TRUE-TARGET TEST CASES (9 to 15) ---

def test_tp_9_java_backend_engineer():
    job = create_sample_job("Java Backend Engineer", "TechCorp", "Worldwide", EmploymentType.FULL_TIME, 120000, 150000, SalaryPeriod.ANNUAL, "Build Java, REST API microservices with PostgreSQL.", ext_id="tp9")
    exp = JobScorer().evaluate_job(job)
    assert exp.role_relevance == RoleRelevance.TARGET_ROLE
    assert exp.technical_match_score >= 85.0
    assert exp.priority_score >= 70.0

def test_tp_10_spring_boot_engineer():
    job = create_sample_job("Spring Boot Engineer", "FinTech Inc", "Remote - EMEA", EmploymentType.FULL_TIME, 110000, 140000, SalaryPeriod.ANNUAL, "Spring Security, Spring Boot, microservices and PostgreSQL.", ext_id="tp10")
    exp = JobScorer().evaluate_job(job)
    assert exp.role_relevance == RoleRelevance.TARGET_ROLE
    assert exp.match_tier == "STRONG_MATCH"
    assert exp.priority_score >= 70.0

def test_tp_11_nodejs_backend_engineer():
    job = create_sample_job("Node.js Backend Engineer", "NodeCo", "Worldwide", EmploymentType.FULL_TIME, 90000, 110000, SalaryPeriod.ANNUAL, "Node.js, TypeScript, Express, REST APIs.", ext_id="tp11")
    exp = JobScorer().evaluate_job(job)
    assert exp.role_relevance == RoleRelevance.TARGET_ROLE
    assert exp.match_tier == "GOOD_MATCH"
    assert exp.priority_score >= 60.0

def test_tp_12_go_backend_engineer():
    job = create_sample_job("Go Backend Engineer", "CloudScale", "Worldwide", EmploymentType.FULL_TIME, 120000, 150000, SalaryPeriod.ANNUAL, "Golang, Kubernetes, gRPC microservices.", ext_id="tp12")
    exp = JobScorer().evaluate_job(job)
    assert exp.role_relevance == RoleRelevance.TARGET_ROLE
    assert exp.match_tier == "TRANSFERABLE"
    assert exp.priority_score >= 60.0

def test_tp_13_ai_coding_evaluator():
    job = create_sample_job("AI Coding Evaluator", "AI Labs", "Worldwide", EmploymentType.CONTRACT, 25, 25, SalaryPeriod.HOURLY, "Evaluate LLM code generation in Java and Python.", ext_id="tp13")
    exp = JobScorer().evaluate_job(job)
    assert exp.role_relevance == RoleRelevance.TARGET_ROLE
    assert "AI_TECHNICAL_EVALUATION" in exp.classifications
    assert "FAST_CASH" in exp.classifications

def test_tp_14_technical_project_manager():
    job = create_sample_job("Technical Project Manager", "DevTools Co", "Worldwide", EmploymentType.FULL_TIME, 90000, 110000, SalaryPeriod.ANNUAL, "Manage software development teams using Scrum and Agile for REST APIs.", ext_id="tp14")
    exp = JobScorer().evaluate_job(job)
    assert exp.role_relevance == RoleRelevance.TARGET_ROLE
    assert "SECONDARY_SKILL" in exp.classifications

def test_tp_15_api_technical_writer():
    job = create_sample_job("API Technical Writer", "API Platform", "Worldwide", EmploymentType.CONTRACT, 35, 35, SalaryPeriod.HOURLY, "Write API documentation and OpenAPI specs for developer APIs.", ext_id="tp15")
    exp = JobScorer().evaluate_job(job)
    assert exp.role_relevance == RoleRelevance.TARGET_ROLE
    assert "SECONDARY_SKILL" in exp.classifications


# --- CASES A - I FROM INITIAL SUITE ---

def test_case_a_java_spring_worldwide_contract():
    job = create_sample_job("Java & Spring Boot Backend Engineer", "GlobalTech", "Worldwide", EmploymentType.CONTRACT, 40.0, 40.0, SalaryPeriod.HOURLY, "Build REST APIs and microservices with Java, Spring Boot, and PostgreSQL.", ext_id="case_a")
    exp = JobScorer().evaluate_job(job)
    assert exp.remote_eligibility == RemoteEligibility.ELIGIBLE
    assert exp.technical_match_score >= 85.0
    assert exp.income_urgency_score >= 80.0
    assert exp.priority_score >= 75.0

def test_case_b_python_backend_us_only():
    job = create_sample_job("Python Backend Developer", "US Startup", "US Only", EmploymentType.FULL_TIME, 100000.0, 100000.0, SalaryPeriod.ANNUAL, "Build FastAPI backends in Python.", ext_id="case_b")
    exp = JobScorer().evaluate_job(job)
    assert exp.remote_eligibility == RemoteEligibility.INELIGIBLE
    assert exp.technical_match_score < 30.0

def test_ranking_views_exclude_non_target():
    storage = JobStorage(db_path=":memory:")
    query_service = JobQueryService(storage=storage)

    jobs = [
        create_sample_job("Senior Java Developer", "FinCorp", "Worldwide", EmploymentType.FULL_TIME, 120000, 140000, SalaryPeriod.ANNUAL, "Java Spring Boot PostgreSQL", ext_id="101"),
        create_sample_job("Renewals Manager", "GitLab", "Worldwide", EmploymentType.FULL_TIME, 150000, 150000, SalaryPeriod.ANNUAL, "Renewals sales", ext_id="102"), # NON_TARGET
        create_sample_job("Nurse Practitioner", "Galileo", "Worldwide", EmploymentType.CONTRACT, 50, 50, SalaryPeriod.HOURLY, "Nursing clinical", ext_id="103"), # NON_TARGET
    ]

    for j in jobs:
        storage.save_normalized_job(j)

    apply_first = query_service.get_apply_first_jobs(limit=5)
    assert len(apply_first) == 1
    assert apply_first[0].job.external_id == "101"
