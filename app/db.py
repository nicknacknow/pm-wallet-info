"""Postgres persistence — single pm_profiles table (wallet is PK)."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import asyncpg

from app.models import PolymarketProfileInfo
from app.settings import ENRICHMENT_TTL_HOURS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS pm_profiles (
    wallet              TEXT PRIMARY KEY,
    profile_status      TEXT NOT NULL DEFAULT 'unknown',
    username            TEXT,
    display_name        TEXT,
    created_at          TIMESTAMPTZ,
    total_trades        INTEGER,
    total_volume        NUMERIC,
    total_realized_pnl  NUMERIC,
    win_rate            NUMERIC,
    avg_pnl_per_trade   NUMERIC,
    portfolio_value     NUMERIC,
    last_enriched_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_pm_profiles_total_trades ON pm_profiles(total_trades);
CREATE INDEX IF NOT EXISTS idx_pm_profiles_total_realized_pnl ON pm_profiles(total_realized_pnl);
"""

_MIGRATION = """
ALTER TABLE pm_profiles DROP CONSTRAINT IF EXISTS pm_profiles_wallet_fkey;
DROP TABLE IF EXISTS wallet_info CASCADE;
"""

# ---------------------------------------------------------------------------
# Upserts
# ---------------------------------------------------------------------------

_UPSERT_PM_PROFILE = """
INSERT INTO pm_profiles (
    wallet, profile_status, username, display_name,
    created_at, total_trades, total_volume, total_realized_pnl,
    win_rate, avg_pnl_per_trade, portfolio_value,
    last_enriched_at
) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
ON CONFLICT (wallet) DO UPDATE SET
    profile_status   = EXCLUDED.profile_status,
    username         = EXCLUDED.username,
    display_name     = EXCLUDED.display_name,
    created_at       = EXCLUDED.created_at,
    total_trades     = EXCLUDED.total_trades,
    total_volume     = EXCLUDED.total_volume,
    total_realized_pnl = EXCLUDED.total_realized_pnl,
    win_rate         = EXCLUDED.win_rate,
    avg_pnl_per_trade = EXCLUDED.avg_pnl_per_trade,
    portfolio_value  = EXCLUDED.portfolio_value,
    last_enriched_at = EXCLUDED.last_enriched_at;
"""

# ---------------------------------------------------------------------------
# Selects
# ---------------------------------------------------------------------------

_SELECT_PM_PROFILE = """
SELECT wallet, profile_status, username, display_name,
       created_at, total_trades, total_volume, total_realized_pnl,
       win_rate, avg_pnl_per_trade, portfolio_value,
       last_enriched_at
FROM pm_profiles WHERE wallet = $1;
"""

_SELECT_LAST_ENRICHED = "SELECT last_enriched_at FROM pm_profiles WHERE wallet = $1;"
_SELECT_ALL_WALLETS   = "SELECT wallet FROM pm_profiles;"

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def bootstrap_schema(conn: asyncpg.Connection) -> None:
    await conn.execute(_SCHEMA)
    logger.info("schema bootstrapped")


async def upsert_pm_profile(conn: asyncpg.Connection, profile: PolymarketProfileInfo) -> None:
    await conn.execute(
        _UPSERT_PM_PROFILE,
        profile.wallet,
        profile.profile_status,
        profile.username,
        profile.display_name,
        profile.created_at,
        profile.total_trades,
        profile.total_volume,
        profile.total_realized_pnl,
        profile.win_rate,
        profile.avg_pnl_per_trade,
        profile.portfolio_value,
        profile.last_enriched_at,
    )
    logger.debug("upserted pm_profile wallet=%s status=%s", profile.wallet, profile.profile_status)


async def fetch_last_enriched_at(conn: asyncpg.Connection, wallet: str) -> datetime | None:
    row = await conn.fetchrow(_SELECT_LAST_ENRICHED, wallet)
    return row["last_enriched_at"] if row else None


async def fetch_pm_profile(conn: asyncpg.Connection, wallet: str) -> dict | None:
    row = await conn.fetchrow(_SELECT_PM_PROFILE, wallet)
    return dict(row) if row else None


async def all_wallet_addresses(conn: asyncpg.Connection) -> list[str]:
    rows = await conn.fetch(_SELECT_ALL_WALLETS)
    return [str(r["wallet"]) for r in rows]


def is_stale(last_enriched_at: datetime, ttl_hours: int = ENRICHMENT_TTL_HOURS) -> bool:
    if last_enriched_at.tzinfo is None:
        last_enriched_at = last_enriched_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - last_enriched_at > timedelta(hours=ttl_hours)
