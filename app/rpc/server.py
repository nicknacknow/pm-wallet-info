"""gRPC server — serves wallet data from the owned Postgres tables."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

import asyncpg

from app.db import fetch_full_profile, fetch_pm_profile, fetch_wallet_info
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

    async def GetWalletInfo(self, request, context):
        async with self._pool.acquire() as conn:
            row = await fetch_wallet_info(conn, request.wallet)
        if row is None:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("wallet not found")
            return wallet_pb2.WalletInfo()
        return wallet_pb2.WalletInfo(
            wallet=row["wallet"],
            polygon_balance=_str(row.get("polygon_balance")),
            tx_count=_int(row.get("tx_count")),
            last_enriched_at=_ts(row.get("last_enriched_at")),
        )

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
            total_volume=_str(row.get("total_volume")),
            pnl=_str(row.get("pnl")),
            num_trades=_int(row.get("num_trades")),
            positions_count=_int(row.get("positions_count")),
            active_positions=_int(row.get("active_positions")),
            positions_value=_str(row.get("positions_value")),
            positions_pnl=_str(row.get("positions_pnl")),
            last_enriched_at=_ts(row.get("last_enriched_at")),
        )

    async def GetFullProfile(self, request, context):
        async with self._pool.acquire() as conn:
            profile = await fetch_full_profile(conn, request.wallet)
        if profile.last_enriched_at is None:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("wallet not found")
            return wallet_pb2.FullProfile()
        return wallet_pb2.FullProfile(
            wallet=profile.wallet,
            polygon_balance=_str(profile.polygon_balance),
            tx_count=_int(profile.tx_count),
            profile_status=_str(profile.profile_status),
            username=_str(profile.username),
            display_name=_str(profile.display_name),
            total_volume=_str(profile.total_volume),
            pnl=_str(profile.pnl),
            num_trades=_int(profile.num_trades),
            positions_count=_int(profile.positions_count),
            active_positions=_int(profile.active_positions),
            positions_value=_str(profile.positions_value),
            last_enriched_at=_ts(profile.last_enriched_at),
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
