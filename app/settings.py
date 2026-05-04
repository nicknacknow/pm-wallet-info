"""Runtime settings for pm-wallet-info."""

from __future__ import annotations

import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/wallet_info",
)
CHANNEL = os.getenv("CHANNEL", "trades.raw")
RETRY_DELAY_SECONDS = int(os.getenv("RETRY_DELAY_SECONDS", "5"))
METRICS_PORT = int(os.getenv("METRICS_PORT", "8002"))
GRPC_PORT = int(os.getenv("GRPC_PORT", "50051"))
ENRICHMENT_TTL_HOURS = int(os.getenv("ENRICHMENT_TTL_HOURS", "24"))
POLYGONSCAN_API_KEY = os.getenv("POLYGONSCAN_API_KEY", "")
POLYGONSCAN_BASE_URL = os.getenv(
    "POLYGONSCAN_BASE_URL",
    "https://api.polygonscan.com/api",
)
POLYMARKET_BASE_URL = os.getenv(
    "POLYMARKET_BASE_URL",
    "https://data-api.polymarket.com/profiles",
)
HTTP_TIMEOUT_SECONDS = float(os.getenv("HTTP_TIMEOUT_SECONDS", "5"))
HTTP_MAX_RETRIES = int(os.getenv("HTTP_MAX_RETRIES", "2"))