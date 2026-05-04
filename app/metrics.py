"""Prometheus metrics for pm-wallet-info."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, start_http_server

from app.settings import METRICS_PORT

REDIS_RETRIES_TOTAL = Counter(
    "pm_wallet_info_redis_retries_total",
    "Total Redis reconnect attempts.",
)
REDIS_CONNECTED = Gauge(
    "pm_wallet_info_redis_connected",
    "Whether pm-wallet-info is connected to Redis.",
)
WALLET_EVENTS_PROCESSED_TOTAL = Counter(
    "pm_wallet_info_wallet_events_processed_total",
    "Total trade events processed for wallet enrichment.",
)
WALLETS_ENRICHED_TOTAL = Counter(
    "pm_wallet_info_wallets_enriched_total",
    "Total wallets enriched successfully.",
)
WALLET_ENRICHMENT_ERRORS_TOTAL = Counter(
    "pm_wallet_info_wallet_enrichment_errors_total",
    "Total wallet enrichment attempts that failed.",
)
MALFORMED_TRADE_EVENTS_TOTAL = Counter(
    "pm_wallet_info_malformed_trade_events_total",
    "Total malformed trade events skipped.",
)

REDIS_CONNECTED.set(0)


def start_metrics_server(port: int = METRICS_PORT) -> None:
    """Expose Prometheus metrics over HTTP."""
    start_http_server(port)


def mark_redis_connected() -> None:
    """Record that Redis is currently reachable."""
    REDIS_CONNECTED.set(1)


def mark_redis_disconnected() -> None:
    """Record that Redis is currently unreachable."""
    REDIS_CONNECTED.set(0)


def record_redis_retry() -> None:
    """Count a Redis reconnect attempt."""
    REDIS_RETRIES_TOTAL.inc()


def record_wallet_event_processed() -> None:
    """Count a processed trade event."""
    WALLET_EVENTS_PROCESSED_TOTAL.inc()


def record_wallet_enriched() -> None:
    """Count a successfully enriched wallet."""
    WALLETS_ENRICHED_TOTAL.inc()


def record_wallet_enrichment_error() -> None:
    """Count a failed wallet enrichment attempt."""
    WALLET_ENRICHMENT_ERRORS_TOTAL.inc()


def record_malformed_trade_event() -> None:
    """Count a malformed event that was skipped."""
    MALFORMED_TRADE_EVENTS_TOTAL.inc()