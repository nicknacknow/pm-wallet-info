"""gRPC server for wallet enrichment data."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

from app.db import fetch_full_profile, fetch_pm_profile, fetch_wallet_info
from app.generated import wallet_pb2, wallet_pb2_grpc


logger = logging.getLogger(__name__)


def _to_timestamp(value: datetime | None) -> Timestamp:
    timestamp = Timestamp()
    if value is None:
        return timestamp
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    timestamp.FromDatetime(value)
    return timestamp


def _build_wallet_info(row: dict[str, object] | None, wallet: str) -> wallet_pb2.WalletInfo:
    if row is None:
        return wallet_pb2.WalletInfo(wallet=wallet)
    return wallet_pb2.WalletInfo(
        wallet=str(row["wallet"]),
        polygon_balance=str(row["polygon_balance"]) if row.get("polygon_balance") is not None else "",
        tx_count=int(row["tx_count"]) if row.get("tx_count") is not None else 0,
        last_enriched_at=_to_timestamp(row.get("last_enriched_at")),
    )


def _build_pm_profile(row: dict[str, object] | None, wallet: str) -> wallet_pb2.PolymarketProfile:
    if row is None:
        return wallet_pb2.PolymarketProfile(wallet=wallet)
    return wallet_pb2.PolymarketProfile(
        wallet=str(row["wallet"]),
        username=str(row["username"]) if row.get("username") is not None else "",
        display_name=str(row["display_name"]) if row.get("display_name") is not None else "",
        total_volume=str(row["total_volume"]) if row.get("total_volume") is not None else "",
        pnl=str(row["pnl"]) if row.get("pnl") is not None else "",
        num_trades=int(row["num_trades"]) if row.get("num_trades") is not None else 0,
        last_enriched_at=_to_timestamp(row.get("last_enriched_at")),
    )


class WalletServicer(wallet_pb2_grpc.WalletServiceServicer):
    """Serve wallet data from the service-owned tables."""

    def __init__(self, db_pool) -> None:
        self._db_pool = db_pool

    async def GetWalletInfo(self, request, context):
        async with self._db_pool.acquire() as connection:
            row = await fetch_wallet_info(connection, request.wallet)
        if row is None:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("wallet not found")
            return wallet_pb2.WalletInfo()
        return _build_wallet_info(row, request.wallet)

    async def GetPolymarketProfile(self, request, context):
        async with self._db_pool.acquire() as connection:
            row = await fetch_pm_profile(connection, request.wallet)
        if row is None:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("wallet profile not found")
            return wallet_pb2.PolymarketProfile()
        return _build_pm_profile(row, request.wallet)

    async def GetFullProfile(self, request, context):
        async with self._db_pool.acquire() as connection:
            row = await fetch_full_profile(connection, request.wallet)
        if row.wallet == request.wallet and row.last_enriched_at is None:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("wallet profile not found")
            return wallet_pb2.FullProfile()
        return wallet_pb2.FullProfile(
            wallet=row.wallet,
            polygon_balance=str(row.polygon_balance) if row.polygon_balance is not None else "",
            tx_count=int(row.tx_count) if row.tx_count is not None else 0,
            username=row.username or "",
            display_name=row.display_name or "",
            total_volume=str(row.total_volume) if row.total_volume is not None else "",
            pnl=str(row.pnl) if row.pnl is not None else "",
            num_trades=int(row.num_trades) if row.num_trades is not None else 0,
            last_enriched_at=_to_timestamp(row.last_enriched_at),
        )


async def run_grpc_server(db_pool, port: int) -> None:
    """Run the gRPC server until cancelled."""
    server = grpc.aio.server()
    wallet_pb2_grpc.add_WalletServiceServicer_to_server(WalletServicer(db_pool), server)
    server.add_insecure_port(f"[::]:{port}")
    await server.start()
    logger.info("gRPC server listening on %s", port)
    try:
        await server.wait_for_termination()
    finally:
        await server.stop(grace=5)