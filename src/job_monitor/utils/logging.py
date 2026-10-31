import logging
import sys
from typing import Optional


def setup_logger(name: str = "job_monitor", level: str = "INFO") -> logging.Logger:
    """Configures and returns a structured logger for application components."""
    logger = logging.getLogger(name)
    
    # Avoid adding duplicate handlers if logger is re-initialized
    if logger.hasHandlers():
        return logger

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
