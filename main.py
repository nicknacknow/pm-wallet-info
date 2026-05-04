"""Run pm-wallet-info."""

from __future__ import annotations

import asyncio
import logging

import asyncpg

from app.db import bootstrap_schema
from app.metrics import start_metrics_server
from app.pubsub.worker import stream_trade_events
from app.rpc.server import run_grpc_server
from app.settings import DATABASE_URL, GRPC_PORT


logger = logging.getLogger(__name__)


async def main() -> None:
    """Start metrics, seed the schema, and run worker + gRPC server."""
    start_metrics_server()
    logger.info("metrics server started")
    db_pool = await asyncpg.create_pool(DATABASE_URL)
    try:
        async with db_pool.acquire() as connection:
            await bootstrap_schema(connection)
        logger.info("database schema bootstrapped")

        await asyncio.gather(
            run_grpc_server(db_pool, GRPC_PORT),
            stream_trade_events(db_pool),
        )
    finally:
        await db_pool.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    asyncio.run(main())