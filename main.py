"""Entrypoint — starts worker + gRPC server concurrently."""
from __future__ import annotations

import asyncio
import logging

import asyncpg

from app.db import bootstrap_schema
from app.pubsub.worker import run_worker
from app.rpc.server import run_grpc_server
from app.settings import DATABASE_URL, GRPC_PORT


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger = logging.getLogger(__name__)

    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    try:
        async with pool.acquire() as conn:
            await bootstrap_schema(conn)
        logger.info("schema ready")

        await asyncio.gather(
            run_grpc_server(pool, GRPC_PORT),
            run_worker(pool),
        )
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
