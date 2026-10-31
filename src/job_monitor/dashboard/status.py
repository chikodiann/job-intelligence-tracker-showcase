"""Thread-safe Pipeline Status Tracker for Ann's Job Intelligence & Application Tracker."""

import threading
from typing import Any, Dict, Optional


class PipelineStatusTracker:
    """Tracks live ingestion, scoring, and operational pipeline execution status."""

    _instance: Optional["PipelineStatusTracker"] = None
    _lock = threading.Lock()

    def __init__(self):
        self.state: str = "IDLE"  # IDLE, STARTING, INGESTING, SCORING, COMPLETE, ERROR
        self.candidate_name: str = "Candidate"
        self.candidate_title: str = "Professional"
        self.active_source: Optional[str] = None
        self.sources: Dict[str, Dict[str, Any]] = {}
        self.summary: Dict[str, int] = {
            "total_fetched": 0,
            "total_new": 0,
            "total_updated": 0,
            "strong_matches": 0,
            "fast_cash": 0,
        }
        self.error: Optional[str] = None

    @classmethod
    def get_instance(cls) -> "PipelineStatusTracker":
        """Returns global thread-safe singleton instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def initialize(self, candidate_name: str, candidate_title: str, source_names: list) -> None:
        """Resets and initializes status tracker for a new pipeline run."""
        with self._lock:
            self.state = "STARTING"
            self.candidate_name = candidate_name
            self.candidate_title = candidate_title
            self.active_source = None
            self.error = None
            self.summary = {
                "total_fetched": 0,
                "total_new": 0,
                "total_updated": 0,
                "strong_matches": 0,
                "fast_cash": 0,
            }
            self.sources = {
                name: {"status": "PENDING", "fetched": 0, "new": 0}
                for name in source_names
            }

    def set_source_starting(self, source_name: str) -> None:
        """Marks a source as actively fetching."""
        with self._lock:
            self.state = "INGESTING"
            self.active_source = source_name
            if source_name in self.sources:
                self.sources[source_name]["status"] = "FETCHING"

    def set_source_completed(self, source_name: str, fetched: int, new: int) -> None:
        """Marks a source as completed with fetched/new counts."""
        with self._lock:
            if source_name in self.sources:
                self.sources[source_name]["status"] = "COMPLETED"
                self.sources[source_name]["fetched"] = fetched
                self.sources[source_name]["new"] = new
            self.summary["total_fetched"] += fetched
            self.summary["total_new"] += new

    def set_source_failed(self, source_name: str, error_msg: str) -> None:
        """Marks a source as failed without stopping the overall pipeline."""
        with self._lock:
            if source_name in self.sources:
                self.sources[source_name]["status"] = "FAILED"
                self.sources[source_name]["error"] = error_msg

    def set_scoring(self) -> None:
        """Marks status as technical scoring in progress."""
        with self._lock:
            self.state = "SCORING"
            self.active_source = None

    def set_complete(self, strong_matches: int = 0, fast_cash: int = 0) -> None:
        """Marks status as complete with final match metrics."""
        with self._lock:
            self.state = "COMPLETE"
            self.active_source = None
            self.summary["strong_matches"] = strong_matches
            self.summary["fast_cash"] = fast_cash

    def set_error(self, error_msg: str) -> None:
        """Marks pipeline status as failed with an error message."""
        with self._lock:
            self.state = "ERROR"
            self.error = error_msg

    def to_dict(self) -> Dict[str, Any]:
        """Returns JSON-serializable dictionary representation of current pipeline status."""
        with self._lock:
            return {
                "state": self.state,
                "candidate_name": self.candidate_name,
                "candidate_title": self.candidate_title,
                "active_source": self.active_source,
                "sources": {k: dict(v) for k, v in self.sources.items()},
                "summary": dict(self.summary),
                "error": self.error,
            }
