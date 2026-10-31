from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from ..db.storage import JobStorage
from ..interfaces.fetcher import BaseJobFetcher
from ..models.normalized_job import NormalizedJob
from ..models.raw_job import RawJob
from ..utils.logging import setup_logger
from ..scoring.eligibility import EligibilityClassifier, RemoteEligibility
from ..scoring.relevance import RoleRelevance, RoleRelevanceClassifier
from .deduplicator import JobDeduplicator
from .normalizer import JobNormalizer

logger = setup_logger("ingestion.pipeline")


class SourceIngestionStats(BaseModel):
    """Execution metrics for a single ingestion source."""
    source_name: str
    fetched: int = 0
    normalized: int = 0
    rejected: int = 0
    eligible: int = 0
    relevant: int = 0
    new: int = 0
    updated: int = 0
    duplicates: int = 0
    failed: int = 0


class IngestionSummary(BaseModel):
    """Complete summary report of an ingestion run."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_fetched: int = 0
    total_new: int = 0
    total_updated: int = 0
    total_duplicates: int = 0
    total_failed: int = 0
    sources: Dict[str, SourceIngestionStats] = Field(default_factory=dict)

    def print_summary(self) -> str:
        """Renders clean human-readable summary string."""
        lines = [
            "=" * 70,
            f"   REMOTE JOB INGESTION SUMMARY ({self.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')})",
            "=" * 70,
            "Source Performance",
            "------------------"
        ]
        for src_name, stats in self.sources.items():
            lines.append(
                f"{src_name:<14} fetched {stats.fetched:<5} | normalized {stats.normalized:<5} | "
                f"eligible {stats.eligible:<5} | relevant {stats.relevant:<5} | "
                f"deduped {stats.duplicates:<5} | new {stats.new:<5} | failed {stats.failed:<3}"
            )
        lines.extend([
            "-" * 70,
            f"TOTALS -> Fetched: {self.total_fetched} | New: {self.total_new} | Updated: {self.total_updated} | Duplicates: {self.total_duplicates} | Failed: {self.total_failed}",
            "=" * 70,
        ])
        return "\n".join(lines)


class IngestionPipeline:
    """Orchestrates fetch -> preserve raw -> normalize -> deduplicate -> persist pipeline."""

    def __init__(
        self,
        storage: JobStorage,
        fetchers: Optional[List[BaseJobFetcher]] = None,
        normalizer: Optional[JobNormalizer] = None,
        deduplicator: Optional[JobDeduplicator] = None,
    ):
        self.storage = storage
        self.fetchers = fetchers or []
        self.normalizer = normalizer or JobNormalizer()
        self.deduplicator = deduplicator or JobDeduplicator(storage=storage)

    def run(self, limit_per_source: Optional[int] = None) -> IngestionSummary:
        """Executes full ingestion pipeline across all configured fetcher sources."""
        logger.info("Starting ingestion pipeline execution across %d sources", len(self.fetchers))
        summary = IngestionSummary()

        for fetcher in self.fetchers:
            stats = SourceIngestionStats(source_name=fetcher.source_name)
            logger.info("Executing ingestion source [%s]...", fetcher.source_name)

            try:
                from ..dashboard.status import PipelineStatusTracker
                PipelineStatusTracker.get_instance().set_source_starting(fetcher.source_name)
            except Exception:
                pass

            # 1. FETCH STAGE (Source Error Boundary)
            raw_jobs: List[RawJob] = []
            try:
                raw_jobs = fetcher.fetch_jobs(limit=limit_per_source)
                stats.fetched = len(raw_jobs)
            except Exception as e:
                logger.error("Source [%s] fetch error: %s", fetcher.source_name, str(e))
                stats.failed += 1
                summary.sources[fetcher.source_name] = stats
                try:
                    from ..dashboard.status import PipelineStatusTracker
                    PipelineStatusTracker.get_instance().set_source_failed(fetcher.source_name, str(e))
                except Exception:
                    pass
                continue


            # 2. PER-JOB PROCESSING (Job Error Boundary)
            for raw_job in raw_jobs:
                try:
                    # Save raw payload for debugging/provenance
                    self.storage.save_raw_payload(raw_job)

                    # Normalize job
                    norm_job = self.normalizer.normalize(raw_job)
                    if not norm_job:
                        logger.warning("Failed to normalize job ID %s from %s", raw_job.external_id, fetcher.source_name)
                        stats.rejected += 1
                        stats.failed += 1
                        continue

                    stats.normalized += 1

                    # Geographic eligibility check for metrics
                    elig_status, _ = EligibilityClassifier.classify(norm_job.location_requirement, norm_job.description_text)
                    if elig_status == RemoteEligibility.ELIGIBLE:
                        stats.eligible += 1

                    # Relevance check for metrics
                    rel_status, _ = RoleRelevanceClassifier.classify_relevance(norm_job)
                    if rel_status != RoleRelevance.NON_TARGET_ROLE:
                        stats.relevant += 1

                    # Check Deduplication
                    dedup_res = self.deduplicator.check_duplicate(norm_job)

                    if dedup_res.is_duplicate and dedup_res.existing_job_id:
                        stats.duplicates += 1
                        # Update last_seen timestamp on existing job record
                        self.storage.update_job_seen(dedup_res.existing_job_id, datetime.now(timezone.utc))
                    else:
                        # Save new or updated record
                        job_id, is_new = self.storage.save_normalized_job(norm_job)
                        if is_new:
                            stats.new += 1
                        else:
                            stats.updated += 1

                except Exception as e:
                    logger.error("Error processing job %s from %s: %s", raw_job.external_id, fetcher.source_name, str(e))
                    stats.failed += 1

            summary.sources[fetcher.source_name] = stats
            try:
                from ..dashboard.status import PipelineStatusTracker
                PipelineStatusTracker.get_instance().set_source_completed(fetcher.source_name, fetched=stats.fetched, new=stats.new)
            except Exception:
                pass

            summary.total_fetched += stats.fetched
            summary.total_new += stats.new
            summary.total_updated += stats.updated
            summary.total_duplicates += stats.duplicates
            summary.total_failed += stats.failed

        logger.info("Ingestion pipeline finished execution.")
        print(summary.print_summary())
        return summary
