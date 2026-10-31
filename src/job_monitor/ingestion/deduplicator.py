import hashlib
from typing import List, Optional, Tuple
from ..db.storage import JobStorage
from ..interfaces.deduplicator import BaseDeduplicator
from ..models.normalized_job import NormalizedJob
from ..utils.logging import setup_logger

logger = setup_logger("ingestion.deduplicator")


class DeduplicationResult:
    """Detailed metadata result of deduplication check."""
    def __init__(self, is_duplicate: bool, match_level: str = "NONE", existing_job_id: Optional[str] = None):
        self.is_duplicate = is_duplicate
        self.match_level = match_level  # "SOURCE_ID", "URL", "FINGERPRINT", "CONTENT_HASH", "NONE"
        self.existing_job_id = existing_job_id


class JobDeduplicator(BaseDeduplicator):
    """Layered deduplication engine checking database and batch uniqueness."""

    def __init__(self, storage: Optional[JobStorage] = None):
        self.storage = storage

    def generate_content_hash(self, job: NormalizedJob) -> str:
        """Generates SHA256 digest of normalized job core content."""
        payload_str = f"{job.company_name.lower().strip()}|{job.title.lower().strip()}|{job.description_text[:300].lower().strip()}"
        return hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

    def generate_canonical_fingerprint(self, job: NormalizedJob) -> str:
        """Generates canonical fingerprint (company + title + location)."""
        c = "".join(ch for ch in job.company_name.lower() if ch.isalnum())
        t = "".join(ch for ch in job.title.lower() if ch.isalnum())
        loc = "".join(ch for ch in (job.location_requirement or "worldwide").lower() if ch.isalnum())
        return f"{c}|{t}|{loc}"

    def check_duplicate(self, job: NormalizedJob) -> DeduplicationResult:
        """Checks whether job matches an existing record in storage using 4-layer strategy.
        
        Layer 1: Exact Source Name + External ID
        Layer 2: Exact Application URL
        Layer 3: Canonical Fingerprint (company + title + location)
        Layer 4: SHA256 Content Hash
        """
        if not self.storage:
            return DeduplicationResult(is_duplicate=False)

        # Layer 1: Exact Source Identity
        existing = self.storage.get_job_by_source_and_ext_id(job.source_name, job.external_id)
        if existing:
            return DeduplicationResult(is_duplicate=True, match_level="SOURCE_ID", existing_job_id=existing.id)

        # Layer 2: Application URL
        if job.url:
            existing = self.storage.get_job_by_url(job.url)
            if existing:
                return DeduplicationResult(is_duplicate=True, match_level="URL", existing_job_id=existing.id)

        # Layer 3: Canonical Fingerprint
        if job.canonical_fingerprint:
            existing = self.storage.get_job_by_fingerprint(job.canonical_fingerprint)
            if existing:
                return DeduplicationResult(is_duplicate=True, match_level="FINGERPRINT", existing_job_id=existing.id)

        # Layer 4: Content Hash
        if job.content_hash:
            existing = self.storage.get_job_by_content_hash(job.content_hash)
            if existing:
                return DeduplicationResult(is_duplicate=True, match_level="CONTENT_HASH", existing_job_id=existing.id)

        return DeduplicationResult(is_duplicate=False, match_level="NONE")

    def deduplicate(self, jobs: List[NormalizedJob]) -> Tuple[List[NormalizedJob], List[NormalizedJob]]:
        """Deduplicates a batch of normalized jobs against database and in-batch duplicates."""
        unique_jobs: List[NormalizedJob] = []
        duplicate_jobs: List[NormalizedJob] = []

        seen_urls = set()
        seen_fingerprints = set()
        seen_hashes = set()

        for job in jobs:
            # Check in-batch duplicates
            if job.url and job.url in seen_urls:
                duplicate_jobs.append(job)
                continue
            if job.canonical_fingerprint and job.canonical_fingerprint in seen_fingerprints:
                duplicate_jobs.append(job)
                continue
            if job.content_hash and job.content_hash in seen_hashes:
                duplicate_jobs.append(job)
                continue

            # Check database duplicates
            res = self.check_duplicate(job)
            if res.is_duplicate:
                duplicate_jobs.append(job)
            else:
                unique_jobs.append(job)
                if job.url:
                    seen_urls.add(job.url)
                if job.canonical_fingerprint:
                    seen_fingerprints.add(job.canonical_fingerprint)
                if job.content_hash:
                    seen_hashes.add(job.content_hash)

        return unique_jobs, duplicate_jobs
