from typing import Dict, List, Optional, Tuple
from .config import load_config
from .db.storage import JobStorage
from .ingestion import (
    ArbeitnowFetcher,
    CryptoJobsFetcher,
    HimalayasFetcher,
    IngestionPipeline,
    IngestionSummary,
    JobicyFetcher,
    RemoteOKFetcher,
    RemotiveFetcher,
    WWRDevOpsFetcher,
    WWRFullstackFetcher,
    WWRRSSFetcher,
)
from .notifications import CompositeNotifier, MacOSDesktopNotifier, WindowsDesktopNotifier, get_platform_notifier
from .notifications.desktop_macos import build_notification_summary
from .reports import DailyReportGenerator, ReportHistoryStore
from .scoring import JobQueryService, JobScorer
from .scoring.candidate_profile import load_candidate_profile
from .utils.logging import setup_logger
from .utils.timezone import get_local_date_str, get_local_now

logger = setup_logger("pipeline_runner")


class OperationalPipelineRunner:
    """End-to-end operational pipeline runner coordinating ingestion, evaluation, reporting, and notification."""

    def __init__(self, config_path: Optional[str] = None, profile_name: Optional[str] = None):
        self.config = load_config(config_path, profile_name=profile_name)
        self.candidate_profile = load_candidate_profile(self.config.active_profile)
        self.storage = JobStorage(self.config.database.path)
        self.scorer = JobScorer(candidate_profile=self.candidate_profile)
        self.query_service = JobQueryService(storage=self.storage, scorer=self.scorer)
        self.report_generator = DailyReportGenerator(query_service=self.query_service)
        self.history_store = ReportHistoryStore(storage=self.storage)

        # Configure Cross-Platform Notifier
        self.notifier = get_platform_notifier()

        # Configure Fetchers Registry
        fetcher_registry = {
            "remotive": (RemotiveFetcher, "https://remotive.com/api/remote-jobs"),
            "jobicy": (JobicyFetcher, "https://jobicy.com/api/v2/remote-jobs"),
            "weworkremotely": (WWRRSSFetcher, "https://weworkremotely.com/remote-jobs.rss"),
            "remoteok": (RemoteOKFetcher, "https://remoteok.com/api"),
            "arbeitnow": (ArbeitnowFetcher, "https://www.arbeitnow.com/api/job-board-api"),
            "himalayas": (HimalayasFetcher, "https://himalayas.app/jobs/rss"),
            "cryptojobs": (CryptoJobsFetcher, "https://cryptojobslist.com/rss.xml"),
            "wwr_fullstack": (WWRFullstackFetcher, "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss"),
            "wwr_devops": (WWRDevOpsFetcher, "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss"),
        }

        self.fetchers = []
        for name, (cls, default_url) in fetcher_registry.items():
            src_cfg = self.config.ingestion.sources.get(name)
            is_enabled = src_cfg.enabled if src_cfg and hasattr(src_cfg, "enabled") else True
            if is_enabled:
                url = src_cfg.url if src_cfg and hasattr(src_cfg, "url") else default_url
                self.fetchers.append(
                    cls(
                        endpoint_url=url,
                        rate_limit_delay_seconds=self.config.ingestion.rate_limit_delay_seconds,
                    )
                )

    def run_full_cycle(
        self,
        limit_per_source: Optional[int] = None,
        is_scheduled: bool = False,
        force: bool = False,
    ) -> str:
        """Executes full operational cycle: fetch -> normalize -> dedup -> score -> rank -> report -> notify."""
        local_date = get_local_date_str()

        if is_scheduled and not force:
            if self.storage.is_morning_run_completed_for_date(local_date):
                msg = f"Today's scheduled morning run ({local_date}) has already completed successfully. Skipping."
                logger.info(msg)
                return msg

        if is_scheduled:
            now_local = get_local_now()
            if now_local.hour > 8 or (now_local.hour == 8 and now_local.minute > 15):
                run_type = "RECOVERY"
            else:
                run_type = "SCHEDULED"
            is_daily_morning = True
        else:
            run_type = "MANUAL"
            is_daily_morning = False

        run_id = self.storage.record_pipeline_run_start(
            run_type=run_type,
            is_daily_morning=is_daily_morning,
            lagos_date=local_date,
        )

        try:
            logger.info(f"Initiating {run_type} operational job intelligence cycle (run_id={run_id})...")
            try:
                from .dashboard.status import PipelineStatusTracker
                PipelineStatusTracker.get_instance().initialize(
                    candidate_name=self.candidate_profile.name,
                    candidate_title=self.candidate_profile.professional_title,
                    source_names=[f.source_name for f in self.fetchers],
                )
            except Exception:
                pass

            # 1. Ingestion Pipeline
            pipeline = IngestionPipeline(storage=self.storage, fetchers=self.fetchers)
            summary: IngestionSummary = pipeline.run(limit_per_source=limit_per_source)

            # 2. Evaluation & Ranking
            try:
                from .dashboard.status import PipelineStatusTracker
                PipelineStatusTracker.get_instance().set_scoring()
            except Exception:
                pass

            apply_first = self.query_service.get_apply_first_jobs(limit=10)

            # 3. Report Generation
            report_markdown = self.report_generator.generate_report()

            # 4. Save Report Run to History & Disk
            source_status = {name: stats.model_dump() for name, stats in summary.sources.items()}
            top_ids = [r.job.id for r in apply_first if r.job.id]

            self.history_store.save_report_run(
                source_status=source_status,
                jobs_fetched=summary.total_fetched,
                jobs_new=summary.total_new,
                jobs_updated=summary.total_updated,
                jobs_closed=0,
                top_job_ids=top_ids,
                report_markdown=report_markdown,
            )

            # 5. Desktop Notification Dispatch
            fast_cash = self.query_service.get_fastest_cash_jobs(limit=5)
            top_fast_cash_title = fast_cash[0].job.title if fast_cash else None
            strong_matches = [
                r for r in apply_first
                if r.explanation.match_tier == "STRONG_MATCH" or r.explanation.priority_score >= 60.0
            ]

            try:
                from .dashboard.status import PipelineStatusTracker
                PipelineStatusTracker.get_instance().set_complete(
                    strong_matches=len(strong_matches),
                    fast_cash=len(fast_cash),
                )
            except Exception:
                pass

            notif = build_notification_summary(
                total_new=summary.total_new,
                total_updated=summary.total_updated,
                strong_match_count=len(strong_matches),
                fast_cash_count=len(fast_cash),
                top_fast_cash_title=top_fast_cash_title,
            )

            if notif:
                title, message, subtitle = notif
                self.notifier.send_notification(title, message, subtitle)
            else:
                logger.info("No meaningful job updates to notify.")

            # Record run success
            self.storage.record_pipeline_run_complete(
                run_id=run_id,
                status="SUCCESS",
                jobs_fetched=summary.total_fetched,
                jobs_new=summary.total_new,
                jobs_updated=summary.total_updated,
            )

            logger.info(f"Operational cycle (run_id={run_id}) completed successfully.")
            return report_markdown

        except Exception as e:
            logger.error(f"Pipeline run {run_id} failed: {e}", exc_info=True)
            try:
                from .dashboard.status import PipelineStatusTracker
                PipelineStatusTracker.get_instance().set_error(str(e))
            except Exception:
                pass
            self.storage.record_pipeline_run_complete(
                run_id=run_id,
                status="FAILED",
                error_message=str(e),
            )
            raise e


    def generate_report_only(self) -> str:
        """Generates report from existing stored jobs without re-fetching."""
        return self.report_generator.generate_report()

