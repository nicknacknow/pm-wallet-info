"""gRPC server — serves wallet data from pm_profiles."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

import asyncpg

from app.db import fetch_pm_profile
from app.generated import wallet_pb2, wallet_pb2_grpc

logger = logging.getLogger(__name__)


def _ts(dt: datetime | None) -> Timestamp:
    t = Timestamp()
    if dt is None:
        return t
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    t.FromDatetime(dt)
    return t


def _str(v: object) -> str:
    return str(v) if v is not None else ""


def _int(v: object) -> int:
    return int(v) if v is not None else 0


class WalletServicer(wallet_pb2_grpc.WalletServiceServicer):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def GetPolymarketProfile(self, request, context):
        async with self._pool.acquire() as conn:
            row = await fetch_pm_profile(conn, request.wallet)
        if row is None:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("wallet profile not found")
            return wallet_pb2.PolymarketProfile()
        return wallet_pb2.PolymarketProfile(
            wallet=row["wallet"],
            profile_status=_str(row.get("profile_status")),
            username=_str(row.get("username")),
            display_name=_str(row.get("display_name")),
            created_at=_ts(row.get("created_at")),
            total_trades=_int(row.get("total_trades")),
            total_volume=_str(row.get("total_volume")),
            total_realized_pnl=_str(row.get("total_realized_pnl")),
            win_rate=_str(row.get("win_rate")),
            avg_pnl_per_trade=_str(row.get("avg_pnl_per_trade")),
            portfolio_value=_str(row.get("portfolio_value")),
            last_enriched_at=_ts(row.get("last_enriched_at")),
        )


async def run_grpc_server(pool: asyncpg.Pool, port: int) -> None:
    server = grpc.aio.server()
    wallet_pb2_grpc.add_WalletServiceServicer_to_server(WalletServicer(pool), server)
    server.add_insecure_port(f"[::]:{port}")
    await server.start()
    logger.info("gRPC server listening on port %d", port)
    try:
        await server.wait_for_termination()
    finally:
        await server.stop(grace=5)
