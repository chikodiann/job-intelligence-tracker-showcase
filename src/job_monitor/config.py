import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from pydantic import BaseModel, Field


class DatabaseConfig(BaseModel):
    path: str = "data/jobs.db"
    pool_timeout_seconds: int = 30


class SourceConfig(BaseModel):
    enabled: bool = True
    url: str


class IngestionConfig(BaseModel):
    user_agent: str = "RemoteJobCashflowMonitor/1.0"
    request_timeout_seconds: int = 15
    rate_limit_delay_seconds: float = 2.0
    sources: Dict[str, SourceConfig] = Field(default_factory=dict)


class CashflowDefaults(BaseModel):
    currency: str = "USD"
    target_annual_cashflow: Optional[float] = None
    target_hourly_rate: Optional[float] = None
    cashflow_objective: str = "BALANCED"
    desired_employment_types: list[str] = Field(default_factory=lambda: ["full_time", "contract", "fractional"])


class DashboardConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8500

    @property
    def canonical_url(self) -> str:
        return f"http://{self.host}:{self.port}"


class AppConfig(BaseModel):
    name: str = "Remote Job & Cashflow Monitor"
    version: str = "0.1.0"
    log_level: str = "INFO"
    active_profile: str = "example"
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    ingestion: IngestionConfig = Field(default_factory=IngestionConfig)
    cashflow_defaults: CashflowDefaults = Field(default_factory=CashflowDefaults)
    dashboard: DashboardConfig = Field(default_factory=DashboardConfig)


def get_profile_db_path(profile_name: str, default_db_path: str = "data/jobs.db") -> str:
    """Resolves profile-specific database path ensuring isolated storage per candidate."""
    from .utils.paths import AppPaths
    return AppPaths.get_database_path(profile_name, default_db_path)


def load_config(config_path: Optional[str] = None, profile_name: Optional[str] = None) -> AppConfig:
    """Loads application configuration from YAML file with environment variable overrides."""
    from .utils.paths import AppPaths
    if config_path is None:
        config_path = str(AppPaths.get_config_path())

    yaml_data: Dict[str, Any] = {}
    path = Path(config_path)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f)
            if isinstance(loaded, dict):
                yaml_data = loaded
                if "app" in yaml_data and isinstance(yaml_data["app"], dict):
                    app_dict = yaml_data.pop("app")
                    for k, v in app_dict.items():
                        yaml_data.setdefault(k, v)

    # Build Pydantic model
    config = AppConfig(**yaml_data)

    # Environment variable or packaged embedded profile overrides
    env_profile = profile_name or os.getenv("JOB_MONITOR_PROFILE")
    if not env_profile and AppPaths.is_packaged():
        embedded = AppPaths.get_embedded_profile_path()
        if embedded and embedded.exists():
            try:
                with open(embedded, "r", encoding="utf-8") as f:
                    prof_data = yaml.safe_load(f)
                    if isinstance(prof_data, dict) and prof_data.get("id"):
                        env_profile = prof_data["id"]
            except Exception:
                pass

    if env_profile:
        config.active_profile = env_profile

    env_db_path = os.getenv("DATABASE_PATH")
    if env_db_path:
        config.database.path = env_db_path
    else:
        config.database.path = get_profile_db_path(config.active_profile, config.database.path)

    env_log_level = os.getenv("LOG_LEVEL")
    if env_log_level:
        config.log_level = env_log_level

    env_dash_host = os.getenv("DASHBOARD_HOST")
    if env_dash_host:
        config.dashboard.host = env_dash_host

    env_dash_port = os.getenv("DASHBOARD_PORT")
    if env_dash_port:
        config.dashboard.port = int(env_dash_port)

    return config

