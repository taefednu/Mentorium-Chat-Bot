"""
Observability package: structured logging, metrics, error tracking
"""
from __future__ import annotations

from .event_log import EventLogService
from .health import (
    check_database_health,
    check_platform_database_health,
    get_health_status,
    get_liveness_status,
    get_readiness_status,
)
from .logging import configure_logging, get_logger
from .metrics import MetricsCollector, get_metrics
from .sentry_config import capture_exception, capture_message, configure_sentry

__all__ = [
    # Logging
    "configure_logging",
    "get_logger",
    # Event logging
    "EventLogService",
    # Health checks
    "check_database_health",
    "check_platform_database_health",
    "get_health_status",
    "get_readiness_status",
    "get_liveness_status",
    # Metrics
    "MetricsCollector",
    "get_metrics",
    # Sentry
    "configure_sentry",
    "capture_exception",
    "capture_message",
]
