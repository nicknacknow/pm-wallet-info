"""Postgres persistence — owns wallet_info and pm_profiles tables."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import asyncpg

from app.models import FullWalletProfile, PolymarketProfileInfo, WalletChainInfo
from app.settings import ENRICHMENT_TTL_HOURS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS wallet_info (
    wallet           TEXT        PRIMARY KEY,
    polygon_balance  NUMERIC,
    tx_count         INTEGER,
    last_enriched_at TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pm_profiles (
    wallet              TEXT PRIMARY KEY REFERENCES wallet_info(wallet) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_wallet_info_last_enriched ON wallet_info(last_enriched_at);
CREATE INDEX IF NOT EXISTS idx_pm_profiles_total_trades    ON pm_profiles(total_trades);
CREATE INDEX IF NOT EXISTS idx_pm_profiles_total_realized_pnl           ON pm_profiles(total_realized_pnl);
"""

# ---------------------------------------------------------------------------
# Upserts
# ---------------------------------------------------------------------------

_UPSERT_WALLET_INFO = """
INSERT INTO wallet_info (wallet, polygon_balance, tx_count, last_enriched_at)
VALUES ($1, $2, $3, $4)
ON CONFLICT (wallet) DO UPDATE SET
    polygon_balance  = EXCLUDED.polygon_balance,
    tx_count         = EXCLUDED.tx_count,
    last_enriched_at = EXCLUDED.last_enriched_at;
"""

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

_SELECT_WALLET_INFO = """
SELECT wallet, polygon_balance, tx_count, last_enriched_at
FROM wallet_info WHERE wallet = $1;
"""

_SELECT_PM_PROFILE = """
SELECT wallet, profile_status, username, display_name,
       created_at, total_trades, total_volume, total_realized_pnl,
       win_rate, avg_pnl_per_trade, portfolio_value,
       last_enriched_at
FROM pm_profiles WHERE wallet = $1;
"""

_SELECT_LAST_ENRICHED = "SELECT last_enriched_at FROM wallet_info WHERE wallet = $1;"
_SELECT_ALL_WALLETS   = "SELECT wallet FROM wallet_info;"

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def bootstrap_schema(conn: asyncpg.Connection) -> None:
    """Create tables and indexes if they don't exist."""
    await conn.execute(_SCHEMA)
    logger.info("schema bootstrapped")


async def upsert_wallet_info(conn: asyncpg.Connection, info: WalletChainInfo) -> None:
    await conn.execute(
        _UPSERT_WALLET_INFO,
        info.wallet,
        info.polygon_balance,
        info.tx_count,
        info.last_enriched_at,
    )
    logger.debug("upserted wallet_info wallet=%s", info.wallet)


async def upsert_pm_profile(conn: asyncpg.Connection, profile: PolymarketProfileInfo) -> None:
    await conn.execute(
        _UPSERT_PM_PROFILE,
        profile.wallet,           # $1
        profile.profile_status,   # $2
        profile.username,         # $3
        profile.display_name,     # $4
        profile.created_at,       # $5
        profile.total_trades,     # $6
        profile.total_volume,     # $7
        profile.total_realized_pnl,  # $8
        profile.win_rate,         # $9
        profile.avg_pnl_per_trade,  # $10
        profile.portfolio_value,  # $11
        profile.last_enriched_at, # $12
    )
    logger.debug("upserted pm_profile wallet=%s status=%s", profile.wallet, profile.profile_status)


async def fetch_last_enriched_at(conn: asyncpg.Connection, wallet: str) -> datetime | None:
    row = await conn.fetchrow(_SELECT_LAST_ENRICHED, wallet)
    return row["last_enriched_at"] if row else None


async def fetch_wallet_info(conn: asyncpg.Connection, wallet: str) -> dict[str, Any] | None:
    row = await conn.fetchrow(_SELECT_WALLET_INFO, wallet)
    return dict(row) if row else None


async def fetch_pm_profile(conn: asyncpg.Connection, wallet: str) -> dict[str, Any] | None:
    row = await conn.fetchrow(_SELECT_PM_PROFILE, wallet)
    return dict(row) if row else None


async def fetch_full_profile(conn: asyncpg.Connection, wallet: str) -> FullWalletProfile:
    wi, pm = await asyncio.gather(
        conn.fetchrow(_SELECT_WALLET_INFO, wallet),
        conn.fetchrow(_SELECT_PM_PROFILE, wallet),
    )
    return FullWalletProfile(
        wallet=wallet,
        polygon_balance=wi["polygon_balance"]  if wi else None,
        tx_count=wi["tx_count"]                if wi else None,
        profile_status=pm["profile_status"]    if pm else None,
        username=pm["username"]                if pm else None,
        display_name=pm["display_name"]        if pm else None,
        created_at=pm["created_at"]            if pm else None,
        total_trades=pm["total_trades"]        if pm else None,
        total_volume=pm["total_volume"]        if pm else None,
        total_realized_pnl=pm["total_realized_pnl"] if pm else None,
        win_rate=pm["win_rate"]                if pm else None,
        avg_pnl_per_trade=pm["avg_pnl_per_trade"] if pm else None,
        portfolio_value=pm["portfolio_value"]  if pm else None,
        last_enriched_at=(
            pm["last_enriched_at"]  if pm  and pm["last_enriched_at"]  else
            wi["last_enriched_at"]  if wi  else None
        ),
    )


async def all_wallet_addresses(conn: asyncpg.Connection) -> list[str]:
    rows = await conn.fetch(_SELECT_ALL_WALLETS)
    return [str(r["wallet"]) for r in rows]


def is_stale(last_enriched_at: datetime, ttl_hours: int = ENRICHMENT_TTL_HOURS) -> bool:
    if last_enriched_at.tzinfo is None:
        last_enriched_at = last_enriched_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - last_enriched_at > timedelta(hours=ttl_hours)


# asyncio needed inside fetch_full_profile
import asyncio  # noqa: E402 — placed after all defs to avoid circular at module level
