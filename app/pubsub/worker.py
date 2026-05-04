"""Redis subscription loop and wallet enrichment orchestration."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

import asyncpg
import redis.asyncio as redis
from redis.exceptions import ConnectionError as RedisConnectionError

from app.api.polymarket import fetch_polymarket_profile
from app.api.polygonscan import fetch_wallet_chain_info
from app.db import (
    seed_seen_wallets,
    upsert_pm_profile,
    upsert_wallet_info,
    warm_seen_wallets,
)
from app.models import WalletChainInfo
from app.metrics import (
    mark_redis_connected,
    mark_redis_disconnected,
    record_malformed_trade_event,
    record_redis_retry,
    record_wallet_enriched,
    record_wallet_enrichment_error,
    record_wallet_event_processed,
)
from app.settings import CHANNEL, REDIS_URL, RETRY_DELAY_SECONDS


logger = logging.getLogger(__name__)


def _extract_wallet(message: dict[str, Any]) -> str | None:
    trade = message.get("trade")
    if not isinstance(trade, dict):
        return None
    wallet = trade.get("wallet")
    return str(wallet) if wallet else None


async def close_redis_subscription(
    redis_client: redis.Redis,
    pubsub: Any,
) -> None:
    with contextlib.suppress(RedisConnectionError, OSError):
        await pubsub.unsubscribe(CHANNEL)
    with contextlib.suppress(RedisConnectionError, OSError):
        await pubsub.aclose()
    with contextlib.suppress(RedisConnectionError, OSError):
        await redis_client.aclose()


async def enrich_wallet(
    db_pool: asyncpg.Pool,
    wallet: str,
) -> None:
    """Fetch external data and upsert the service-owned tables."""
    logger.info("enriching wallet=%s", wallet)
    chain_task = fetch_wallet_chain_info(wallet)
    profile_task = fetch_polymarket_profile(wallet)

    chain_result, profile_result = await asyncio.gather(
        chain_task,
        profile_task,
        return_exceptions=True,
    )

    wallet_info = chain_result if not isinstance(chain_result, Exception) else None
    if wallet_info is None and not isinstance(profile_result, Exception):
        wallet_info = WalletChainInfo(
            wallet=wallet,
            polygon_balance=None,
            tx_count=None,
            last_enriched_at=datetime.now(timezone.utc),
        )

    async with db_pool.acquire() as connection:
        if wallet_info is not None:
            await upsert_wallet_info(connection, wallet_info)
            logger.info("stored polygon data for wallet=%s", wallet)
        if not isinstance(profile_result, Exception):
            await upsert_pm_profile(connection, profile_result)
            logger.info("stored polymarket profile for wallet=%s", wallet)

    if isinstance(chain_result, Exception) and isinstance(profile_result, Exception):
        logger.exception("wallet enrichment failed for wallet=%s", wallet)
        raise RuntimeError("wallet enrichment failed for both external sources")

    logger.info("wallet enrichment complete for wallet=%s", wallet)


async def process_wallet_event(
    db_pool: asyncpg.Pool,
    redis_client: redis.Redis,
    wallet: str,
) -> None:
    """Refresh wallet data for every live trade event."""
    is_known = await redis_client.sismember("seen_wallets", wallet)

    if not is_known:
        logger.info("new wallet detected wallet=%s", wallet)
        await redis_client.sadd("seen_wallets", wallet)
    else:
        logger.info("seen wallet refresh wallet=%s", wallet)

    await enrich_wallet(db_pool, wallet)
    record_wallet_enriched()


async def stream_trade_events_once(db_pool: asyncpg.Pool) -> None:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    pubsub = redis_client.pubsub()

    try:
        logger.info("connecting to Redis at %s for %s", REDIS_URL, CHANNEL)
        await pubsub.subscribe(CHANNEL)
        mark_redis_connected()
        logger.info("connected to Redis; listening on %s", CHANNEL)

        async with db_pool.acquire() as connection:
            known_wallets = await warm_seen_wallets(connection)
        await seed_seen_wallets(redis_client, known_wallets)
        logger.info("warmed seen_wallets cache with %s wallets", len(known_wallets))

        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue

            raw_data = message.get("data")
            if not isinstance(raw_data, str):
                continue

            try:
                payload = json.loads(raw_data)
                wallet = _extract_wallet(payload)
                if wallet is None:
                    record_malformed_trade_event()
                    logger.warning("skipping trade event without wallet")
                    continue

                record_wallet_event_processed()
                logger.info("processed trade event for wallet=%s", wallet)
                await process_wallet_event(db_pool, redis_client, wallet)
            except (
                KeyError,
                TypeError,
                ValueError,
                json.JSONDecodeError,
                RuntimeError,
                asyncpg.PostgresError,
            ) as exc:
                record_malformed_trade_event()
                record_wallet_enrichment_error()
                logger.exception("skipping malformed trade event: %s", exc)
    finally:
        mark_redis_disconnected()
        await close_redis_subscription(redis_client, pubsub)


async def stream_trade_events(db_pool: asyncpg.Pool) -> None:
    while True:
        try:
            await stream_trade_events_once(db_pool)
        except RedisConnectionError as exc:
            record_redis_retry()
            logger.warning("Redis unavailable: %s", exc)
            logger.info("waiting %ss before retrying", RETRY_DELAY_SECONDS)
            await asyncio.sleep(RETRY_DELAY_SECONDS)
            logger.info("retrying Redis connection")