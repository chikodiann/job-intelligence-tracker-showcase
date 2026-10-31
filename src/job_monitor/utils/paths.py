"""Centralized filesystem path resolution for read-only resources and OS-specific writable user data."""

import os
import sys
from pathlib import Path
from typing import Optional


class AppPaths:
    """Manages application directory paths separating read-only application resources from writable user data."""

    _override_data_dir: Optional[Path] = None

    @classmethod
    def set_data_dir_override(cls, data_dir: Optional[Path]) -> None:
        """Sets an optional explicit data directory override (useful for unit testing)."""
        cls._override_data_dir = data_dir

    @classmethod
    def is_packaged(cls) -> bool:
        """Returns True if the application is running inside a PyInstaller frozen bundle."""
        return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")

    @classmethod
    def get_bundle_dir(cls) -> Path:
        """Returns read-only application resource directory (sys._MEIPASS in bundle or repository root in dev)."""
        if cls.is_packaged():
            return Path(sys._MEIPASS)
        # Development root directory
        return Path(__file__).resolve().parent.parent.parent.parent

    @classmethod
    def get_user_data_dir(cls) -> Path:
        """Returns OS-specific per-user writable application data directory."""
        if cls._override_data_dir:
            cls._override_data_dir.mkdir(parents=True, exist_ok=True)
            return cls._override_data_dir

        env_data_dir = os.getenv("JOB_MONITOR_DATA_DIR")
        if env_data_dir:
            p = Path(env_data_dir)
            p.mkdir(parents=True, exist_ok=True)
            return p

        # Packaged mode: Use OS standard per-user application support directory
        if cls.is_packaged():
            if sys.platform == "darwin":
                base = Path.home() / "Library" / "Application Support" / "JobIntelligenceTracker"
            elif sys.platform == "win32":
                local_app_data = os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local")
                base = Path(local_app_data) / "AnnsJobTracker"
            else:
                base = Path.home() / ".config" / "AnnsJobTracker"
        else:
            # Development mode: Project root directory
            base = cls.get_bundle_dir()

        base.mkdir(parents=True, exist_ok=True)
        return base

    @classmethod
    def get_database_path(cls, profile_id: str = "example", default_db: Optional[str] = None) -> str:
        """Resolves profile-specific writable database path."""
        env_db_path = os.getenv("DATABASE_PATH")
        if env_db_path:
            return env_db_path

        if default_db and default_db != "data/jobs.db":
            return default_db

        p = (profile_id or "example").lower().strip()
        data_base = cls.get_user_data_dir()

        if p in ("example", "default") and not cls.is_packaged():
            # Dev-mode fallback for the example profile database
            example_path = data_base / "data" / "example" / "jobs.db"
            base_path = data_base / "data" / "jobs.db"
            if example_path.exists():
                return str(example_path)
            return str(base_path)

        # Isolated database directory per candidate profile
        prof_dir = data_base / "data" / p
        prof_dir.mkdir(parents=True, exist_ok=True)
        return str(prof_dir / "jobs.db")

    @classmethod
    def get_config_path(cls) -> Path:
        """Returns path to application configuration YAML file."""
        if cls.is_packaged():
            # In packaged mode, config resides in writable user data directory
            config_file = cls.get_user_data_dir() / "config.yaml"
            if not config_file.exists():
                # Copy embedded default config if present
                embedded_config = cls.get_bundle_dir() / "config.yaml"
                if embedded_config.exists():
                    import shutil
                    shutil.copy(embedded_config, config_file)
            return config_file
        else:
            return cls.get_bundle_dir() / "config.yaml"

    @classmethod
    def get_logs_dir(cls) -> Path:
        """Returns writable directory for application log files."""
        logs_dir = cls.get_user_data_dir() / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        return logs_dir

    @classmethod
    def get_reports_dir(cls) -> Path:
        """Returns writable directory for daily reports."""
        reports_dir = cls.get_user_data_dir() / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        return reports_dir

    @classmethod
    def get_exports_dir(cls) -> Path:
        """Returns writable directory for Excel workbook exports."""
        exports_dir = cls.get_user_data_dir() / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        return exports_dir

    @classmethod
    def get_embedded_profile_path(cls) -> Optional[Path]:
        """Returns path to embedded candidate profile in PyInstaller bundle if present."""
        embedded = cls.get_bundle_dir() / "embedded_profile.yaml"
        if embedded.exists():
            return embedded
        return None
