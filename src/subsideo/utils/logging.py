"""Loguru-based structured logging setup for subsideo."""
from __future__ import annotations

import sys

from loguru import logger


def configure_logging(verbose: bool = False) -> None:
    """Configure loguru logger. Call once at CLI entry point."""
    logger.remove()
    level = "DEBUG" if verbose else "INFO"
    logger.add(
        sys.stderr,
        level=level,
        colorize=True,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    )
