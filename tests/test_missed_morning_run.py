"""Tests for Phase 12 — Missed Morning Run Recovery and Idempotency Guard."""

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
import pytest
from zoneinfo import ZoneInfo

from job_monitor.db.storage import JobStorage
from job_monitor.pipeline_runner import OperationalPipelineRunner
from job_monitor.utils.timezone import LAGOS_TZ, get_lagos_date_str, get_lagos_now
from job_monitor.cli import main as cli_main


@pytest.fixture
def temp_storage():
    return JobStorage(":memory:")


class TestTimezoneUtils:
    def test_lagos_date_str_formatting(self):
        """Verifies Lagos date string calculation across naive and aware datetimes."""
        dt_utc = datetime(2026, 10, 8, 23, 30, tzinfo=timezone.utc)
        # 23:30 UTC on Oct 8 is 00:30 WAT on Oct 9 in Africa/Lagos (+1)
        lagos_date = get_lagos_date_str(dt_utc)
        assert lagos_date == "2026-10-09"

    def test_lagos_now(self):
        """Verifies get_lagos_now returns datetime with Africa/Lagos tzinfo."""
        now = get_lagos_now()
        assert now.tzinfo == LAGOS_TZ


class TestDailyMorningRunGuard:
    def test_no_previous_run_execution(self, temp_storage):
        """A. Morning run at 08:00 when no previous run exists -> executes."""
        dt_0800 = datetime(2026, 10, 8, 8, 0, tzinfo=LAGOS_TZ)
        lagos_date = "2026-10-08"

        assert not temp_storage.is_morning_run_completed_for_date(lagos_date)

        run_id = temp_storage.record_pipeline_run_start(
            run_type="SCHEDULED", is_daily_morning=True, lagos_date=lagos_date
        )
        temp_storage.record_pipeline_run_complete(
            run_id=run_id, status="SUCCESS", jobs_fetched=10, jobs_new=2
        )

        assert temp_storage.is_morning_run_completed_for_date(lagos_date)
        status_info = temp_storage.get_morning_run_status(lagos_date=lagos_date, now_dt=dt_0800)
        assert status_info["status"] == "COMPLETED"

    def test_missed_run_recovery_execution(self, temp_storage):
        """B. Morning run starts at 08:30 and today's run is missing -> executes recovery."""
        dt_0830 = datetime(2026, 10, 8, 8, 30, tzinfo=LAGOS_TZ)
        lagos_date = "2026-10-08"

        # Check before run
        assert not temp_storage.is_morning_run_completed_for_date(lagos_date)
        status_before = temp_storage.get_morning_run_status(lagos_date=lagos_date, now_dt=dt_0830)
        assert status_before["status"] == "MISSED"

        # Simulate recovery run
        run_id = temp_storage.record_pipeline_run_start(
            run_type="RECOVERY", is_daily_morning=True, lagos_date=lagos_date
        )
        temp_storage.record_pipeline_run_complete(
            run_id=run_id, status="SUCCESS", jobs_fetched=15, jobs_new=3
        )

        assert temp_storage.is_morning_run_completed_for_date(lagos_date)
        status_after = temp_storage.get_morning_run_status(lagos_date=lagos_date, now_dt=dt_0830)
        assert status_after["status"] == "COMPLETED"

    def test_already_succeeded_today_skips(self, temp_storage):
        """C. Morning run at 08:30 when today's morning run already succeeded -> does not execute again."""
        lagos_date = get_lagos_date_str()

        # Record earlier successful morning run
        run_id = temp_storage.record_pipeline_run_start(
            run_type="SCHEDULED", is_daily_morning=True, lagos_date=lagos_date
        )
        temp_storage.record_pipeline_run_complete(
            run_id=run_id, status="SUCCESS", jobs_fetched=10
        )

        runner = OperationalPipelineRunner()
        runner.storage = temp_storage

        # Mock fetchers / pipeline to verify they are NOT called
        with patch.object(runner.history_store, "save_report_run") as mock_save:
            res = runner.run_full_cycle(is_scheduled=True)
            assert "already completed successfully" in res
            mock_save.assert_not_called()

    def test_manual_run_does_not_count_as_morning_run(self, temp_storage):
        """D. Manual run does not count as today's scheduled morning run."""
        lagos_date = "2026-10-08"

        # Record manual run
        run_id = temp_storage.record_pipeline_run_start(
            run_type="MANUAL", is_daily_morning=False, lagos_date=lagos_date
        )
        temp_storage.record_pipeline_run_complete(
            run_id=run_id, status="SUCCESS", jobs_fetched=20
        )

        # Scheduled morning run should still be pending
        assert not temp_storage.is_morning_run_completed_for_date(lagos_date)

    def test_failed_morning_run_retry(self, temp_storage):
        """E. Failed morning run can be retried later."""
        lagos_date = "2026-10-08"

        # Record failed morning run attempt
        run_id = temp_storage.record_pipeline_run_start(
            run_type="SCHEDULED", is_daily_morning=True, lagos_date=lagos_date
        )
        temp_storage.record_pipeline_run_complete(
            run_id=run_id, status="FAILED", error_message="Network Timeout"
        )

        # Check morning run completed returns False so retry can happen
        assert not temp_storage.is_morning_run_completed_for_date(lagos_date)

        dt_0845 = datetime(2026, 10, 8, 8, 45, tzinfo=LAGOS_TZ)
        status_info = temp_storage.get_morning_run_status(lagos_date=lagos_date, now_dt=dt_0845)
        assert status_info["status"] == "FAILED"

        # Retry recovery run succeeds
        run_id_2 = temp_storage.record_pipeline_run_start(
            run_type="RECOVERY", is_daily_morning=True, lagos_date=lagos_date
        )
        temp_storage.record_pipeline_run_complete(
            run_id_2, status="SUCCESS", jobs_fetched=10
        )

        assert temp_storage.is_morning_run_completed_for_date(lagos_date)

    def test_repeated_wake_events_prevent_duplicate_runs(self, temp_storage):
        """F. Repeated wake/start events do not duplicate the daily run."""
        lagos_date = get_lagos_date_str()
        runner = OperationalPipelineRunner()
        runner.storage = temp_storage

        # First wake triggers recovery run
        with patch.object(runner.notifier, "send_notification"), \
             patch("job_monitor.pipeline_runner.IngestionPipeline.run") as mock_ingest:
            mock_ingest.return_value = MagicMock(total_fetched=10, total_new=2, total_updated=0, sources={})

            res1 = runner.run_full_cycle(is_scheduled=True)
            assert isinstance(res1, str) and "JOB INTELLIGENCE" in res1
            assert temp_storage.is_morning_run_completed_for_date(lagos_date)

        # Second wake at 10:00 AM tries scheduled run again
        with patch("job_monitor.pipeline_runner.IngestionPipeline.run") as mock_ingest_2:
            res2 = runner.run_full_cycle(is_scheduled=True)
            assert "already completed successfully" in res2
            mock_ingest_2.assert_not_called()

        # Third wake at 11:00 AM tries scheduled run again
        with patch("job_monitor.pipeline_runner.IngestionPipeline.run") as mock_ingest_3:
            res3 = runner.run_full_cycle(is_scheduled=True)
            assert "already completed successfully" in res3
            mock_ingest_3.assert_not_called()

    def test_notification_not_duplicated_on_skip(self, temp_storage):
        """H. Notification is not sent when scheduled run is skipped."""
        lagos_date = get_lagos_date_str()
        runner = OperationalPipelineRunner()
        runner.storage = temp_storage

        # Pre-mark today as completed
        run_id = temp_storage.record_pipeline_run_start(
            run_type="SCHEDULED", is_daily_morning=True, lagos_date=lagos_date
        )
        temp_storage.record_pipeline_run_complete(run_id, status="SUCCESS")

        with patch.object(runner.notifier, "send_notification") as mock_notify:
            res = runner.run_full_cycle(is_scheduled=True)
            assert "already completed successfully" in res
            mock_notify.assert_not_called()

    def test_status_cli_output(self, capsys, temp_storage):
        """I. Tests CLI status output includes morning run status."""
        with patch("job_monitor.cli.OperationalPipelineRunner") as mock_runner_cls:
            mock_runner = MagicMock()
            mock_runner.storage = temp_storage
            mock_runner_cls.return_value = mock_runner

            cli_main(["status"])
            captured = capsys.readouterr()
            assert "JOB MONITOR SYSTEM STATUS" in captured.out
            assert "Morning Run Status:" in captured.out
