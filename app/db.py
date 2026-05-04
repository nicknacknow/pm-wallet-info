"""Postgres persistence for wallet enrichment data."""

from __future__ import annotations

import json
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
    profile_status TEXT NOT NULL DEFAULT 'unknown',
    username TEXT,
    display_name TEXT,
    total_volume NUMERIC,
    pnl NUMERIC,
    num_trades INTEGER,
    stats_status TEXT NOT NULL DEFAULT 'unknown',
    positions_status TEXT NOT NULL DEFAULT 'unknown',
    profile_created_at TIMESTAMPTZ,
    proxy_wallet TEXT,
    profile_image TEXT,
    display_username_public BOOLEAN,
    bio TEXT,
    pseudonym TEXT,
    x_username TEXT,
    verified_badge BOOLEAN,
    profile_payload JSONB,
    positions_count INTEGER,
    active_positions_count INTEGER,
    positions_current_value NUMERIC,
    positions_cash_pnl NUMERIC,
    positions_realized_pnl NUMERIC,
    positions_total_bought NUMERIC,
    positions_initial_value NUMERIC,
    positions_payload JSONB,
    last_enriched_at TIMESTAMPTZ
);
"""

ALTER_PM_PROFILES_ADD_PROFILE_CREATED_AT_SQL = """
ALTER TABLE pm_profiles
ADD COLUMN IF NOT EXISTS profile_created_at TIMESTAMPTZ;
"""

ALTER_PM_PROFILES_ADD_PROFILE_STATUS_SQL = """
ALTER TABLE pm_profiles
ADD COLUMN IF NOT EXISTS profile_status TEXT NOT NULL DEFAULT 'unknown';
"""

ALTER_PM_PROFILES_ADD_PROXY_WALLET_SQL = """
ALTER TABLE pm_profiles
ADD COLUMN IF NOT EXISTS proxy_wallet TEXT;
"""

ALTER_PM_PROFILES_ADD_PROFILE_IMAGE_SQL = """
ALTER TABLE pm_profiles
ADD COLUMN IF NOT EXISTS profile_image TEXT;
"""

ALTER_PM_PROFILES_ADD_DISPLAY_USERNAME_PUBLIC_SQL = """
ALTER TABLE pm_profiles
ADD COLUMN IF NOT EXISTS display_username_public BOOLEAN;
"""

ALTER_PM_PROFILES_ADD_BIO_SQL = """
ALTER TABLE pm_profiles
ADD COLUMN IF NOT EXISTS bio TEXT;
"""

ALTER_PM_PROFILES_ADD_PSEUDONYM_SQL = """
ALTER TABLE pm_profiles
ADD COLUMN IF NOT EXISTS pseudonym TEXT;
"""

ALTER_PM_PROFILES_ADD_X_USERNAME_SQL = """
ALTER TABLE pm_profiles
ADD COLUMN IF NOT EXISTS x_username TEXT;
"""

ALTER_PM_PROFILES_ADD_VERIFIED_BADGE_SQL = """
ALTER TABLE pm_profiles
ADD COLUMN IF NOT EXISTS verified_badge BOOLEAN;
"""

ALTER_PM_PROFILES_ADD_PROFILE_PAYLOAD_SQL = """
ALTER TABLE pm_profiles
ADD COLUMN IF NOT EXISTS profile_payload JSONB;
"""

ALTER_PM_PROFILES_ADD_STATS_STATUS_SQL = """
ALTER TABLE pm_profiles
ADD COLUMN IF NOT EXISTS stats_status TEXT NOT NULL DEFAULT 'unknown';
"""

ALTER_PM_PROFILES_ADD_POSITIONS_STATUS_SQL = """
ALTER TABLE pm_profiles
ADD COLUMN IF NOT EXISTS positions_status TEXT NOT NULL DEFAULT 'unknown';
"""

ALTER_PM_PROFILES_ADD_POSITIONS_COUNT_SQL = """
ALTER TABLE pm_profiles
ADD COLUMN IF NOT EXISTS positions_count INTEGER;
"""

ALTER_PM_PROFILES_ADD_ACTIVE_POSITIONS_COUNT_SQL = """
ALTER TABLE pm_profiles
ADD COLUMN IF NOT EXISTS active_positions_count INTEGER;
"""

ALTER_PM_PROFILES_ADD_POSITIONS_CURRENT_VALUE_SQL = """
ALTER TABLE pm_profiles
ADD COLUMN IF NOT EXISTS positions_current_value NUMERIC;
"""

ALTER_PM_PROFILES_ADD_POSITIONS_CASH_PNL_SQL = """
ALTER TABLE pm_profiles
ADD COLUMN IF NOT EXISTS positions_cash_pnl NUMERIC;
"""

ALTER_PM_PROFILES_ADD_POSITIONS_REALIZED_PNL_SQL = """
ALTER TABLE pm_profiles
ADD COLUMN IF NOT EXISTS positions_realized_pnl NUMERIC;
"""

ALTER_PM_PROFILES_ADD_POSITIONS_TOTAL_BOUGHT_SQL = """
ALTER TABLE pm_profiles
ADD COLUMN IF NOT EXISTS positions_total_bought NUMERIC;
"""

ALTER_PM_PROFILES_ADD_POSITIONS_INITIAL_VALUE_SQL = """
ALTER TABLE pm_profiles
ADD COLUMN IF NOT EXISTS positions_initial_value NUMERIC;
"""

ALTER_PM_PROFILES_ADD_POSITIONS_PAYLOAD_SQL = """
ALTER TABLE pm_profiles
ADD COLUMN IF NOT EXISTS positions_payload JSONB;
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
    profile_status,
    username,
    display_name,
    total_volume,
    pnl,
    num_trades,
    stats_status,
    positions_status,
    profile_created_at,
    proxy_wallet,
    profile_image,
    display_username_public,
    bio,
    pseudonym,
    x_username,
    verified_badge,
    profile_payload,
    positions_count,
    active_positions_count,
    positions_current_value,
    positions_cash_pnl,
    positions_realized_pnl,
    positions_total_bought,
    positions_initial_value,
    positions_payload,
    last_enriched_at
)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25)
ON CONFLICT (wallet) DO UPDATE SET
    profile_status = EXCLUDED.profile_status,
    username = EXCLUDED.username,
    display_name = EXCLUDED.display_name,
    total_volume = EXCLUDED.total_volume,
    pnl = EXCLUDED.pnl,
    num_trades = EXCLUDED.num_trades,
    stats_status = EXCLUDED.stats_status,
    positions_status = EXCLUDED.positions_status,
    profile_created_at = EXCLUDED.profile_created_at,
    proxy_wallet = EXCLUDED.proxy_wallet,
    profile_image = EXCLUDED.profile_image,
    display_username_public = EXCLUDED.display_username_public,
    bio = EXCLUDED.bio,
    pseudonym = EXCLUDED.pseudonym,
    x_username = EXCLUDED.x_username,
    verified_badge = EXCLUDED.verified_badge,
    profile_payload = EXCLUDED.profile_payload,
    positions_count = EXCLUDED.positions_count,
    active_positions_count = EXCLUDED.active_positions_count,
    positions_current_value = EXCLUDED.positions_current_value,
    positions_cash_pnl = EXCLUDED.positions_cash_pnl,
    positions_realized_pnl = EXCLUDED.positions_realized_pnl,
    positions_total_bought = EXCLUDED.positions_total_bought,
    positions_initial_value = EXCLUDED.positions_initial_value,
    positions_payload = EXCLUDED.positions_payload,
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
SELECT wallet, profile_status, username, display_name, total_volume, pnl, num_trades, stats_status, positions_status, profile_created_at, proxy_wallet, profile_image, display_username_public, bio, pseudonym, x_username, verified_badge, profile_payload, positions_count, active_positions_count, positions_current_value, positions_cash_pnl, positions_realized_pnl, positions_total_bought, positions_initial_value, positions_payload, last_enriched_at
FROM pm_profiles
WHERE wallet = $1;
"""


async def bootstrap_schema(connection: asyncpg.Connection) -> None:
    """Create the tables and indexes owned by this service."""
    await connection.execute(CREATE_WALLET_INFO_SQL)
    await connection.execute(CREATE_PM_PROFILES_SQL)
    await connection.execute(ALTER_PM_PROFILES_ADD_PROFILE_STATUS_SQL)
    await connection.execute(ALTER_PM_PROFILES_ADD_PROFILE_CREATED_AT_SQL)
    await connection.execute(ALTER_PM_PROFILES_ADD_PROXY_WALLET_SQL)
    await connection.execute(ALTER_PM_PROFILES_ADD_PROFILE_IMAGE_SQL)
    await connection.execute(ALTER_PM_PROFILES_ADD_DISPLAY_USERNAME_PUBLIC_SQL)
    await connection.execute(ALTER_PM_PROFILES_ADD_BIO_SQL)
    await connection.execute(ALTER_PM_PROFILES_ADD_PSEUDONYM_SQL)
    await connection.execute(ALTER_PM_PROFILES_ADD_X_USERNAME_SQL)
    await connection.execute(ALTER_PM_PROFILES_ADD_VERIFIED_BADGE_SQL)
    await connection.execute(ALTER_PM_PROFILES_ADD_PROFILE_PAYLOAD_SQL)
    await connection.execute(ALTER_PM_PROFILES_ADD_STATS_STATUS_SQL)
    await connection.execute(ALTER_PM_PROFILES_ADD_POSITIONS_STATUS_SQL)
    await connection.execute(ALTER_PM_PROFILES_ADD_POSITIONS_COUNT_SQL)
    await connection.execute(ALTER_PM_PROFILES_ADD_ACTIVE_POSITIONS_COUNT_SQL)
    await connection.execute(ALTER_PM_PROFILES_ADD_POSITIONS_CURRENT_VALUE_SQL)
    await connection.execute(ALTER_PM_PROFILES_ADD_POSITIONS_CASH_PNL_SQL)
    await connection.execute(ALTER_PM_PROFILES_ADD_POSITIONS_REALIZED_PNL_SQL)
    await connection.execute(ALTER_PM_PROFILES_ADD_POSITIONS_TOTAL_BOUGHT_SQL)
    await connection.execute(ALTER_PM_PROFILES_ADD_POSITIONS_INITIAL_VALUE_SQL)
    await connection.execute(ALTER_PM_PROFILES_ADD_POSITIONS_PAYLOAD_SQL)
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
        profile.profile_status,
        profile.username,
        profile.display_name,
        profile.total_volume,
        profile.pnl,
        profile.num_trades,
        profile.stats_status,
        profile.positions_status,
        profile.profile_created_at,
        profile.proxy_wallet,
        profile.profile_image,
        profile.display_username_public,
        profile.bio,
        profile.pseudonym,
        profile.x_username,
        profile.verified_badge,
        json.dumps(profile.profile_payload) if profile.profile_payload is not None else None,
        profile.positions_count,
        profile.active_positions_count,
        profile.positions_current_value,
        profile.positions_cash_pnl,
        profile.positions_realized_pnl,
        profile.positions_total_bought,
        profile.positions_initial_value,
        json.dumps(profile.positions_payload) if profile.positions_payload is not None else None,
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