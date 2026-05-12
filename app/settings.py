"""Runtime settings — every value overridable via environment variable."""
from __future__ import annotations
import os

# Redis
REDIS_URL    = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CHANNEL      = os.getenv("CHANNEL", "trades.raw")

# Postgres
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/trade_store",
)

# gRPC / metrics
GRPC_PORT    = int(os.getenv("GRPC_PORT", "50051"))
METRICS_PORT = int(os.getenv("METRICS_PORT", "8002"))

# Enrichment
ENRICHMENT_TTL_HOURS = int(os.getenv("ENRICHMENT_TTL_HOURS", "24"))
RETRY_DELAY_SECONDS  = int(os.getenv("RETRY_DELAY_SECONDS", "5"))

# External APIs
POLYMARKET_PROFILE_URL = os.getenv(
    "POLYMARKET_PROFILE_URL",
    "https://gamma-api.polymarket.com/public-profile",
)
POLYMARKET_CLOSED_POS_URL = os.getenv(
    "POLYMARKET_CLOSED_POS_URL",
    "https://data-api.polymarket.com/closed-positions",
)
POLYMARKET_VALUE_URL = os.getenv(
    "POLYMARKET_VALUE_URL",
    "https://data-api.polymarket.com/value",
)

# HTTP client
HTTP_TIMEOUT_SECONDS = float(os.getenv("HTTP_TIMEOUT_SECONDS", "8"))
HTTP_MAX_RETRIES     = int(os.getenv("HTTP_MAX_RETRIES", "2"))
