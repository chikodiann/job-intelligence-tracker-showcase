import os
from pathlib import Path
from job_monitor.config import load_config, AppConfig


def test_load_config_defaults(tmp_path: Path):
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text("""
app:
  name: "Test App"
database:
  path: "test.db"
ingestion:
  rate_limit_delay_seconds: 1.5
""")
    config = load_config(str(yaml_file))
    assert config.name == "Test App"
    assert config.database.path == "test.db"
    assert config.ingestion.rate_limit_delay_seconds == 1.5


def test_load_config_env_overrides(tmp_path: Path, monkeypatch):
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text("database:\n  path: 'file.db'\n")
    
    monkeypatch.setenv("DATABASE_PATH", "override.db")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    
    config = load_config(str(yaml_file))
    assert config.database.path == "override.db"
    assert config.log_level == "DEBUG"
