"""Postgres persistence for wallet enrichment data."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

import asyncpg

from app.models import FullWalletProfile, PolymarketProfileInfo, WalletChainInfo

CREATE_WALLET_INFO_SQL = """
CREATE TABLE IF NOT EXISTS wallet_info (
    wallet TEXT PRIMARY KEY,
    polygon_balance NUMERIC,
    tx_count INTEGER,
    last_enriched_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

CREATE_PM_PROFILES_SQL = """
CREATE TABLE IF NOT EXISTS pm_profiles (
    wallet TEXT PRIMARY KEY REFERENCES wallet_info(wallet) ON DELETE CASCADE,
    username TEXT,
    display_name TEXT,
    total_volume NUMERIC,
    pnl NUMERIC,
    num_trades INTEGER,
    last_enriched_at TIMESTAMPTZ
);
"""

CREATE_WALLET_INFO_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_wallet_info_last_enriched
    ON wallet_info(last_enriched_at);
"""

CREATE_PM_PROFILES_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_pm_profiles_num_trades
    ON pm_profiles(num_trades);
"""

UPSERT_WALLET_INFO_SQL = """
INSERT INTO wallet_info (
    wallet,
    polygon_balance,
    tx_count,
    last_enriched_at
)
VALUES ($1, $2, $3, $4)
ON CONFLICT (wallet) DO UPDATE SET
    polygon_balance = EXCLUDED.polygon_balance,
    tx_count = EXCLUDED.tx_count,
    last_enriched_at = EXCLUDED.last_enriched_at;
"""

UPSERT_PM_PROFILE_SQL = """
INSERT INTO pm_profiles (
    wallet,
    username,
    display_name,
    total_volume,
    pnl,
    num_trades,
    last_enriched_at
)
VALUES ($1, $2, $3, $4, $5, $6, $7)
ON CONFLICT (wallet) DO UPDATE SET
    username = EXCLUDED.username,
    display_name = EXCLUDED.display_name,
    total_volume = EXCLUDED.total_volume,
    pnl = EXCLUDED.pnl,
    num_trades = EXCLUDED.num_trades,
    last_enriched_at = EXCLUDED.last_enriched_at;
"""

SELECT_LAST_ENRICHED_AT_SQL = """
SELECT last_enriched_at
FROM wallet_info
WHERE wallet = $1;
"""

SELECT_WALLET_INFO_SQL = """
SELECT wallet, polygon_balance, tx_count, last_enriched_at
FROM wallet_info
WHERE wallet = $1;
"""

SELECT_PM_PROFILE_SQL = """
SELECT wallet, username, display_name, total_volume, pnl, num_trades, last_enriched_at
FROM pm_profiles
WHERE wallet = $1;
"""


async def bootstrap_schema(connection: asyncpg.Connection) -> None:
    """Create the tables and indexes owned by this service."""
    await connection.execute(CREATE_WALLET_INFO_SQL)
    await connection.execute(CREATE_PM_PROFILES_SQL)
    await connection.execute(CREATE_WALLET_INFO_INDEX_SQL)
    await connection.execute(CREATE_PM_PROFILES_INDEX_SQL)


async def warm_seen_wallets(connection: asyncpg.Connection) -> list[str]:
    """Load known wallets from Postgres so Redis can be warmed on startup."""
    rows = await connection.fetch("SELECT wallet FROM wallet_info")
    return [str(row["wallet"]) for row in rows]


async def upsert_wallet_info(
    connection: asyncpg.Connection,
    info: WalletChainInfo,
) -> None:
    """Store wallet-level chain data."""
    await connection.execute(
        UPSERT_WALLET_INFO_SQL,
        info.wallet,
        info.polygon_balance,
        info.tx_count,
        info.last_enriched_at,
    )


async def upsert_pm_profile(
    connection: asyncpg.Connection,
    profile: PolymarketProfileInfo,
) -> None:
    """Store Polymarket profile data."""
    await connection.execute(
        UPSERT_PM_PROFILE_SQL,
        profile.wallet,
        profile.username,
        profile.display_name,
        profile.total_volume,
        profile.pnl,
        profile.num_trades,
        profile.last_enriched_at,
    )


async def fetch_last_enriched_at(
    connection: asyncpg.Connection,
    wallet: str,
) -> datetime | None:
    """Return the last enrichment timestamp for a wallet, if present."""
    row = await connection.fetchrow(SELECT_LAST_ENRICHED_AT_SQL, wallet)
    if row is None:
        return None
    return row["last_enriched_at"]


async def fetch_wallet_info(
    connection: asyncpg.Connection,
    wallet: str,
) -> dict[str, Any] | None:
    """Fetch a wallet_info row by wallet."""
    row = await connection.fetchrow(SELECT_WALLET_INFO_SQL, wallet)
    return dict(row) if row is not None else None


async def fetch_pm_profile(
    connection: asyncpg.Connection,
    wallet: str,
) -> dict[str, Any] | None:
    """Fetch a pm_profiles row by wallet."""
    row = await connection.fetchrow(SELECT_PM_PROFILE_SQL, wallet)
    return dict(row) if row is not None else None


async def fetch_full_profile(
    connection: asyncpg.Connection,
    wallet: str,
) -> FullWalletProfile:
    """Fetch the combined wallet and profile view."""
    wallet_info = await connection.fetchrow(SELECT_WALLET_INFO_SQL, wallet)
    profile = await connection.fetchrow(SELECT_PM_PROFILE_SQL, wallet)
    return FullWalletProfile(
        wallet=wallet,
        polygon_balance=wallet_info["polygon_balance"] if wallet_info is not None else None,
        tx_count=wallet_info["tx_count"] if wallet_info is not None else None,
        username=profile["username"] if profile is not None else None,
        display_name=profile["display_name"] if profile is not None else None,
        total_volume=profile["total_volume"] if profile is not None else None,
        pnl=profile["pnl"] if profile is not None else None,
        num_trades=profile["num_trades"] if profile is not None else None,
        last_enriched_at=(
            profile["last_enriched_at"]
            if profile is not None and profile["last_enriched_at"] is not None
            else wallet_info["last_enriched_at"]
            if wallet_info is not None
            else None
        ),
    )


async def seed_seen_wallets(
    redis_client: Any,
    wallets: Iterable[str],
) -> None:
    """Seed the Redis set used as a warm cache of seen wallets."""
    wallets_list = list(wallets)
    if not wallets_list:
        return
    await redis_client.sadd("seen_wallets", *wallets_list)