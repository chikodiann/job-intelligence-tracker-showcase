import hashlib
import re
from typing import List, Optional
from ..interfaces.normalizer import BaseNormalizer
from ..models.normalized_job import EmploymentType, NormalizedJob, SalaryPeriod
from ..models.raw_job import RawJob
from ..utils.logging import setup_logger
from .parsers import DateParser, HTMLSanitizer, SalaryParser

logger = setup_logger("ingestion.normalizer")


class JobNormalizer(BaseNormalizer):
    """Unified normalizer converting raw job payloads into canonical NormalizedJob models."""

    def normalize(self, raw_job: RawJob) -> Optional[NormalizedJob]:
        """Routes raw job payload to appropriate source parsing method."""
        if not raw_job or not raw_job.payload:
            return None

        try:
            if raw_job.source_name == "remotive":
                return self._normalize_remotive(raw_job)
            elif raw_job.source_name == "jobicy":
                return self._normalize_jobicy(raw_job)
            elif raw_job.source_name in ("weworkremotely", "wwr_fullstack", "wwr_devops"):
                return self._normalize_weworkremotely(raw_job)
            elif raw_job.source_name == "remoteok":
                return self._normalize_remoteok(raw_job)
            elif raw_job.source_name == "arbeitnow":
                return self._normalize_arbeitnow(raw_job)
            elif raw_job.source_name == "himalayas":
                return self._normalize_himalayas(raw_job)
            elif raw_job.source_name == "cryptojobs":
                return self._normalize_cryptojobs(raw_job)
            else:
                return self._normalize_generic(raw_job)
        except Exception as e:
            logger.error("Error normalizing %s job ID %s: %s", raw_job.source_name, raw_job.external_id, str(e))
            return None

    def _normalize_remotive(self, raw_job: RawJob) -> NormalizedJob:
        p = raw_job.payload
        title = (p.get("title") or "").strip()
        company = (p.get("company_name") or "").strip()
        url = (p.get("url") or "").strip()
        
        desc_raw = p.get("description") or ""
        desc_text = HTMLSanitizer.sanitize(desc_raw)

        raw_salary = p.get("salary") or ""
        s_min, s_max, s_curr, s_period, ann_min, ann_max = SalaryParser.parse_salary(raw_salary)

        job_type_str = str(p.get("job_type") or "").lower()
        emp_type = self._map_employment_type(job_type_str)

        location = p.get("candidate_required_location") or "Worldwide"
        posted_at = DateParser.parse_date(p.get("publication_date"))

        tags = p.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        fingerprint = self._compute_fingerprint(company, title, location)
        content_hash = self._compute_content_hash(company, title, desc_text)

        return NormalizedJob(
            source_name=raw_job.source_name,
            external_id=raw_job.external_id,
            url=url,
            title=title,
            company_name=company,
            is_remote=True,
            location_requirement=location,
            employment_type=emp_type,
            salary_min=s_min,
            salary_max=s_max,
            salary_currency=s_curr,
            salary_period=s_period,
            annualized_min_usd=ann_min,
            annualized_max_usd=ann_max,
            original_salary_text=raw_salary if raw_salary else None,
            category=p.get("category"),
            tags=tags,
            description_raw=desc_raw,
            description_text=desc_text,
            content_hash=content_hash,
            canonical_fingerprint=fingerprint,
            posted_at=posted_at,
            fetched_at=raw_job.fetched_at,
        )

    def _normalize_jobicy(self, raw_job: RawJob) -> NormalizedJob:
        p = raw_job.payload
        title = (p.get("jobTitle") or p.get("title") or "").strip()
        company = (p.get("companyName") or p.get("company") or "").strip()
        url = (p.get("url") or "").strip()

        desc_raw = p.get("jobDescription") or p.get("jobExcerpt") or p.get("description") or ""
        desc_text = HTMLSanitizer.sanitize(desc_raw)

        # Jobicy provides salary as string or min/max numeric fields
        raw_salary = p.get("salary")
        if not raw_salary:
            min_s = p.get("annualSalaryMin")
            max_s = p.get("annualSalaryMax")
            if min_s or max_s:
                raw_salary = f"${min_s or ''} - ${max_s or ''}"
        raw_salary = str(raw_salary or "")
        
        s_min, s_max, s_curr, s_period, ann_min, ann_max = SalaryParser.parse_salary(str(raw_salary))

        job_type_str = str(p.get("jobType") or p.get("job_type") or "").lower()
        emp_type = self._map_employment_type(job_type_str)

        location = p.get("jobGeo") or p.get("location") or "Worldwide"
        posted_at = DateParser.parse_date(p.get("pubDate") or p.get("publicationDate"))

        category = p.get("jobCategory") or p.get("jobIndustry") or p.get("category")
        if isinstance(category, list):
            category = ", ".join(str(c) for c in category if c) if category else None
        elif category:
            category = str(category)
        tags = p.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        fingerprint = self._compute_fingerprint(company, title, location)
        content_hash = self._compute_content_hash(company, title, desc_text)

        return NormalizedJob(
            source_name=raw_job.source_name,
            external_id=raw_job.external_id,
            url=url,
            title=title,
            company_name=company,
            is_remote=True,
            location_requirement=location,
            employment_type=emp_type,
            salary_min=s_min,
            salary_max=s_max,
            salary_currency=s_curr,
            salary_period=s_period,
            annualized_min_usd=ann_min,
            annualized_max_usd=ann_max,
            original_salary_text=str(raw_salary) if raw_salary else None,
            category=category,
            tags=tags,
            description_raw=desc_raw,
            description_text=desc_text,
            content_hash=content_hash,
            canonical_fingerprint=fingerprint,
            posted_at=posted_at,
            fetched_at=raw_job.fetched_at,
        )

    def _normalize_weworkremotely(self, raw_job: RawJob) -> NormalizedJob:
        p = raw_job.payload
        full_title = (p.get("title") or "").strip()
        url = (p.get("link") or "").strip()

        # Split "Company Name: Job Title" format commonly used by WWR
        if ":" in full_title:
            parts = full_title.split(":", 1)
            company = parts[0].strip()
            title = parts[1].strip()
        else:
            company = "Unknown"
            title = full_title

        desc_raw = p.get("description") or ""
        desc_text = HTMLSanitizer.sanitize(desc_raw)

        # Attempt to parse salary text embedded inside description or title
        s_min, s_max, s_curr, s_period, ann_min, ann_max = SalaryParser.parse_salary(desc_text[:500])

        posted_at = DateParser.parse_date(p.get("pubDate"))
        category = p.get("category")
        location = "Worldwide"

        fingerprint = self._compute_fingerprint(company, title, location)
        content_hash = self._compute_content_hash(company, title, desc_text)

        return NormalizedJob(
            source_name=raw_job.source_name,
            external_id=raw_job.external_id,
            url=url,
            title=title,
            company_name=company,
            is_remote=True,
            location_requirement=location,
            employment_type=EmploymentType.UNKNOWN,
            salary_min=s_min,
            salary_max=s_max,
            salary_currency=s_curr,
            salary_period=s_period,
            annualized_min_usd=ann_min,
            annualized_max_usd=ann_max,
            original_salary_text=None,
            category=category,
            tags=[],
            description_raw=desc_raw,
            description_text=desc_text,
            content_hash=content_hash,
            canonical_fingerprint=fingerprint,
            posted_at=posted_at,
            fetched_at=raw_job.fetched_at,
        )

    def _normalize_remoteok(self, raw_job: RawJob) -> NormalizedJob:
        p = raw_job.payload
        title = (p.get("position") or p.get("title") or "").strip()
        company = (p.get("company") or "").strip()
        url = (p.get("apply_url") or p.get("url") or "").strip()

        desc_raw = p.get("description") or ""
        desc_text = HTMLSanitizer.sanitize(desc_raw)

        s_min = p.get("salary_min")
        s_max = p.get("salary_max")
        try:
            s_min = float(s_min) if s_min and float(s_min) > 0 else None
        except Exception:
            s_min = None
        try:
            s_max = float(s_max) if s_max and float(s_max) > 0 else None
        except Exception:
            s_max = None

        s_curr = "USD" if (s_min or s_max) else None
        s_period = SalaryPeriod.ANNUAL if (s_min or s_max) else SalaryPeriod.UNKNOWN
        ann_min = s_min
        ann_max = s_max

        location = p.get("location") or "Worldwide"
        posted_at = DateParser.parse_date(p.get("date") or p.get("epoch"))

        tags = p.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        fingerprint = self._compute_fingerprint(company, title, location)
        content_hash = self._compute_content_hash(company, title, desc_text)

        return NormalizedJob(
            source_name=raw_job.source_name,
            external_id=raw_job.external_id,
            url=url,
            title=title,
            company_name=company,
            is_remote=True,
            location_requirement=location,
            employment_type=EmploymentType.UNKNOWN,
            salary_min=s_min,
            salary_max=s_max,
            salary_currency=s_curr,
            salary_period=s_period,
            annualized_min_usd=ann_min,
            annualized_max_usd=ann_max,
            original_salary_text=f"${int(s_min or 0)} - ${int(s_max or 0)}" if (s_min or s_max) else None,
            category=None,
            tags=tags,
            description_raw=desc_raw,
            description_text=desc_text,
            content_hash=content_hash,
            canonical_fingerprint=fingerprint,
            posted_at=posted_at,
            fetched_at=raw_job.fetched_at,
        )

    def _normalize_arbeitnow(self, raw_job: RawJob) -> NormalizedJob:
        p = raw_job.payload
        title = (p.get("title") or "").strip()
        company = (p.get("company_name") or "").strip()
        url = (p.get("url") or "").strip()

        desc_raw = p.get("description") or ""
        desc_text = HTMLSanitizer.sanitize(desc_raw)

        s_min, s_max, s_curr, s_period, ann_min, ann_max = SalaryParser.parse_salary(desc_text[:500])

        is_remote = bool(p.get("remote"))
        location_raw = (p.get("location") or "").strip()
        if is_remote or "remote" in location_raw.lower() or "anywhere" in location_raw.lower():
            location = "Worldwide"
        else:
            location = location_raw or "Worldwide"

        job_types = p.get("job_types") or []
        job_type_str = ", ".join(job_types) if isinstance(job_types, list) else str(job_types)
        emp_type = self._map_employment_type(job_type_str)

        posted_at = DateParser.parse_date(p.get("created_at"))

        tags = p.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        fingerprint = self._compute_fingerprint(company, title, location)
        content_hash = self._compute_content_hash(company, title, desc_text)

        return NormalizedJob(
            source_name=raw_job.source_name,
            external_id=raw_job.external_id,
            url=url,
            title=title,
            company_name=company,
            is_remote=is_remote,
            location_requirement=location,
            employment_type=emp_type,
            salary_min=s_min,
            salary_max=s_max,
            salary_currency=s_curr,
            salary_period=s_period,
            annualized_min_usd=ann_min,
            annualized_max_usd=ann_max,
            category=None,
            tags=tags,
            description_raw=desc_raw,
            description_text=desc_text,
            content_hash=content_hash,
            canonical_fingerprint=fingerprint,
            posted_at=posted_at,
            fetched_at=raw_job.fetched_at,
        )

    def _normalize_himalayas(self, raw_job: RawJob) -> NormalizedJob:
        p = raw_job.payload
        full_title = (p.get("title") or "").strip()
        url = (p.get("link") or "").strip()

        if ":" in full_title:
            parts = full_title.split(":", 1)
            company = parts[0].strip()
            title = parts[1].strip()
        else:
            company = "Himalayas Employer"
            title = full_title

        desc_raw = p.get("description") or ""
        desc_text = HTMLSanitizer.sanitize(desc_raw)

        s_min, s_max, s_curr, s_period, ann_min, ann_max = SalaryParser.parse_salary(desc_text[:500])

        posted_at = DateParser.parse_date(p.get("pubDate"))
        categories = p.get("category") or []
        cat_str = ", ".join(categories) if isinstance(categories, list) else str(categories)
        location = "Worldwide"

        fingerprint = self._compute_fingerprint(company, title, location)
        content_hash = self._compute_content_hash(company, title, desc_text)

        return NormalizedJob(
            source_name=raw_job.source_name,
            external_id=raw_job.external_id,
            url=url,
            title=title,
            company_name=company,
            is_remote=True,
            location_requirement=location,
            employment_type=EmploymentType.UNKNOWN,
            salary_min=s_min,
            salary_max=s_max,
            salary_currency=s_curr,
            salary_period=s_period,
            annualized_min_usd=ann_min,
            annualized_max_usd=ann_max,
            category=cat_str if cat_str else None,
            tags=categories if isinstance(categories, list) else [],
            description_raw=desc_raw,
            description_text=desc_text,
            content_hash=content_hash,
            canonical_fingerprint=fingerprint,
            posted_at=posted_at,
            fetched_at=raw_job.fetched_at,
        )

    def _normalize_cryptojobs(self, raw_job: RawJob) -> NormalizedJob:
        p = raw_job.payload
        full_title = (p.get("title") or "").strip()
        url = (p.get("link") or "").strip()

        if " at " in full_title.lower():
            parts = re.split(r"\s+at\s+", full_title, maxsplit=1, flags=re.IGNORECASE)
            title = parts[0].strip()
            company = parts[1].strip()
        else:
            company = "CryptoJobs Employer"
            title = full_title

        desc_raw = p.get("description") or ""
        desc_text = HTMLSanitizer.sanitize(desc_raw)

        s_min, s_max, s_curr, s_period, ann_min, ann_max = SalaryParser.parse_salary(desc_text[:500])

        posted_at = DateParser.parse_date(p.get("pubDate"))
        categories = p.get("category") or []
        location = "Worldwide"

        fingerprint = self._compute_fingerprint(company, title, location)
        content_hash = self._compute_content_hash(company, title, desc_text)

        return NormalizedJob(
            source_name=raw_job.source_name,
            external_id=raw_job.external_id,
            url=url,
            title=title,
            company_name=company,
            is_remote=True,
            location_requirement=location,
            employment_type=EmploymentType.UNKNOWN,
            salary_min=s_min,
            salary_max=s_max,
            salary_currency=s_curr,
            salary_period=s_period,
            annualized_min_usd=ann_min,
            annualized_max_usd=ann_max,
            category=", ".join(categories) if isinstance(categories, list) and categories else None,
            tags=categories if isinstance(categories, list) else [],
            description_raw=desc_raw,
            description_text=desc_text,
            content_hash=content_hash,
            canonical_fingerprint=fingerprint,
            posted_at=posted_at,
            fetched_at=raw_job.fetched_at,
        )

    def _normalize_generic(self, raw_job: RawJob) -> NormalizedJob:
        p = raw_job.payload
        title = str(p.get("title") or p.get("job_title") or "Untitled")
        company = str(p.get("company") or p.get("company_name") or "Unknown")
        url = str(p.get("url") or p.get("link") or "")
        desc_raw = str(p.get("description") or "")
        desc_text = HTMLSanitizer.sanitize(desc_raw)

        fingerprint = self._compute_fingerprint(company, title, "Worldwide")
        content_hash = self._compute_content_hash(company, title, desc_text)

        return NormalizedJob(
            source_name=raw_job.source_name,
            external_id=raw_job.external_id,
            url=url,
            title=title,
            company_name=company,
            is_remote=True,
            location_requirement="Worldwide",
            description_raw=desc_raw,
            description_text=desc_text,
            content_hash=content_hash,
            canonical_fingerprint=fingerprint,
            fetched_at=raw_job.fetched_at,
        )

    @staticmethod
    def _map_employment_type(job_type_str: str) -> EmploymentType:
        j = job_type_str.lower()
        if "full" in j or "ft" in j:
            return EmploymentType.FULL_TIME
        elif "part" in j or "pt" in j:
            return EmploymentType.PART_TIME
        elif "contract" in j or "freelance" in j:
            return EmploymentType.CONTRACT
        elif "fractional" in j:
            return EmploymentType.FRACTIONAL
        elif "intern" in j:
            return EmploymentType.INTERNSHIP
        return EmploymentType.UNKNOWN

    @staticmethod
    def _compute_fingerprint(company: str, title: str, location: str) -> str:
        c = "".join(ch for ch in company.lower() if ch.isalnum())
        t = "".join(ch for ch in title.lower() if ch.isalnum())
        loc = "".join(ch for ch in location.lower() if ch.isalnum())
        return f"{c}|{t}|{loc}"

    @staticmethod
    def _compute_content_hash(company: str, title: str, desc_text: str) -> str:
        # Use first 300 chars of normalized text for signature hash
        payload_str = f"{company.lower().strip()}|{title.lower().strip()}|{desc_text[:300].lower().strip()}"
        return hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
