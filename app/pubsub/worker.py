"""Redis subscriber — detects new/stale wallets and triggers enrichment."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

import asyncpg
import redis.asyncio as aioredis
from redis.exceptions import ConnectionError as RedisConnectionError

from app.api.polymarket import fetch_polymarket_profile
from app.api.polygonscan import fetch_wallet_chain_info
from app.db import (
    all_wallet_addresses,
    fetch_last_enriched_at,
    is_stale,
    upsert_pm_profile,
    upsert_wallet_info,
)
from app.models import WalletChainInfo
from app.settings import CHANNEL, ENRICHMENT_TTL_HOURS, REDIS_URL, RETRY_DELAY_SECONDS

logger = logging.getLogger(__name__)

_SEEN_KEY = "seen_wallets"


# ---------------------------------------------------------------------------
# Enrichment
# ---------------------------------------------------------------------------

async def enrich_wallet(pool: asyncpg.Pool, wallet: str) -> None:
    """Fetch Polygonscan + Polymarket concurrently, then upsert both tables."""
    logger.info("enriching wallet=%s", wallet)
    chain_res, profile_res = await asyncio.gather(
        fetch_wallet_chain_info(wallet),
        fetch_polymarket_profile(wallet),
        return_exceptions=True,
    )

    # wallet_info must exist before pm_profiles (FK constraint)
    chain_info: WalletChainInfo
    if isinstance(chain_res, Exception):
        logger.warning("polygonscan failed for wallet=%s: %s", wallet, chain_res)
        chain_info = WalletChainInfo(
            wallet=wallet,
            polygon_balance=None,
            tx_count=None,
            last_enriched_at=datetime.now(timezone.utc),
        )
    else:
        chain_info = chain_res

    async with pool.acquire() as conn:
        await upsert_wallet_info(conn, chain_info)

        if isinstance(profile_res, Exception):
            logger.warning("polymarket failed for wallet=%s: %s", wallet, profile_res)
        else:
            await upsert_pm_profile(conn, profile_res)

    logger.info("enrichment complete wallet=%s", wallet)


# ---------------------------------------------------------------------------
# Per-event logic
# ---------------------------------------------------------------------------

async def handle_wallet(pool: asyncpg.Pool, redis: aioredis.Redis, wallet: str) -> None:
    is_known = await redis.sismember(_SEEN_KEY, wallet)

    if not is_known:
        # Atomically claim this wallet — SADD returns 1 if added, 0 if already present.
        # If 0, another concurrent event already claimed it and enrichment is in-flight.
        claimed = await redis.sadd(_SEEN_KEY, wallet)
        if claimed == 0:
            logger.debug("wallet claimed by concurrent event, skipping wallet=%s", wallet)
            return
        logger.info("new wallet detected, enriching wallet=%s", wallet)
        await enrich_wallet(pool, wallet)
        return

    # Known wallet — only re-enrich if data is stale
    async with pool.acquire() as conn:
        last_enriched = await fetch_last_enriched_at(conn, wallet)

    if last_enriched is None or is_stale(last_enriched, ENRICHMENT_TTL_HOURS):
        logger.info(
            "known wallet is stale, re-enriching wallet=%s last_enriched=%s",
            wallet,
            last_enriched.isoformat() if last_enriched else "never",
        )
        await enrich_wallet(pool, wallet)
    else:
        logger.debug(
            "known wallet is fresh, skipping wallet=%s last_enriched=%s",
            wallet,
            last_enriched.isoformat(),
        )


def _extract_wallet(raw: str) -> str | None:
    try:
        payload = json.loads(raw)
        trade = payload.get("trade")
        if not isinstance(trade, dict):
            return None
        wallet = trade.get("wallet")
        return str(wallet) if wallet else None
    except (json.JSONDecodeError, AttributeError):
        return None


# ---------------------------------------------------------------------------
# Subscription loop
# ---------------------------------------------------------------------------

async def _run_once(pool: asyncpg.Pool) -> None:
    """Single connection attempt — subscribe, warm cache, process events."""
    redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    pubsub = redis.pubsub()

    try:
        await pubsub.subscribe(CHANNEL)
        logger.info("subscribed to channel=%s", CHANNEL)

        # Warm the seen_wallets SET from Postgres on startup
        async with pool.acquire() as conn:
            known = await all_wallet_addresses(conn)
        if known:
            await redis.sadd(_SEEN_KEY, *known)
        logger.info("warmed seen_wallets with %d wallets", len(known))

        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            raw = message.get("data")
            if not isinstance(raw, str):
                continue

            wallet = _extract_wallet(raw)
            if wallet is None:
                logger.warning("malformed trade event, skipping: %r", raw[:120])
                continue

            try:
                await handle_wallet(pool, redis, wallet)
            except Exception as exc:
                logger.exception("enrichment error for wallet=%s: %s", wallet, exc)

    finally:
        try:
            await pubsub.unsubscribe(CHANNEL)
            await pubsub.aclose()
            await redis.aclose()
        except Exception:
            pass


async def run_worker(pool: asyncpg.Pool) -> None:
    """Outer retry loop — reconnects on Redis failures."""
    while True:
        try:
            await _run_once(pool)
        except RedisConnectionError as exc:
            logger.warning("Redis connection lost: %s — retrying in %ds", exc, RETRY_DELAY_SECONDS)
            await asyncio.sleep(RETRY_DELAY_SECONDS)
        except Exception as exc:
            logger.exception("worker crashed unexpectedly: %s — retrying in %ds", exc, RETRY_DELAY_SECONDS)
            await asyncio.sleep(RETRY_DELAY_SECONDS)
