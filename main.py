"""Entrypoint — starts the gRPC server."""
from __future__ import annotations

import asyncio
import logging

from app.rpc.server import run_grpc_server
from app.settings import GRPC_PORT


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger = logging.getLogger(__name__)

    await run_grpc_server(GRPC_PORT)


if __name__ == "__main__":
    asyncio.run(main())
