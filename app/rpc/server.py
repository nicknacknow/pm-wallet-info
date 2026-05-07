"""gRPC server — serves wallet data directly from external APIs."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

from app.api.polymarket import fetch_polymarket_profile
from app.api.polygonscan import fetch_wallet_chain_info
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
    async def GetWalletInfo(self, request, context):
        try:
            info = await fetch_wallet_chain_info(request.wallet)
        except Exception:
            logger.exception("failed to fetch wallet info wallet=%s", request.wallet)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("failed to fetch wallet info")
            return wallet_pb2.WalletInfo()
        return wallet_pb2.WalletInfo(
            wallet=info.wallet,
            polygon_balance=_str(info.polygon_balance),
            tx_count=_int(info.tx_count),
            last_enriched_at=_ts(info.last_enriched_at),
        )

    async def GetPolymarketProfile(self, request, context):
        try:
            profile = await fetch_polymarket_profile(request.wallet)
        except Exception:
            logger.exception("failed to fetch polymarket profile wallet=%s", request.wallet)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("failed to fetch polymarket profile")
            return wallet_pb2.PolymarketProfile()
        return wallet_pb2.PolymarketProfile(
            wallet=profile.wallet,
            profile_status=_str(profile.profile_status),
            username=_str(profile.username),
            display_name=_str(profile.display_name),
            created_at=_ts(profile.created_at),
            total_trades=_int(profile.total_trades),
            total_volume=_str(profile.total_volume),
            total_realized_pnl=_str(profile.total_realized_pnl),
            win_rate=_str(profile.win_rate),
            avg_pnl_per_trade=_str(profile.avg_pnl_per_trade),
            portfolio_value=_str(profile.portfolio_value),
            last_enriched_at=_ts(profile.last_enriched_at),
        )

    async def GetFullProfile(self, request, context):
        chain_res, profile_res = await asyncio.gather(
            fetch_wallet_chain_info(request.wallet),
            fetch_polymarket_profile(request.wallet),
            return_exceptions=True,
        )

        if isinstance(chain_res, Exception) and isinstance(profile_res, Exception):
            logger.error(
                "failed to fetch full profile wallet=%s chain_error=%s profile_error=%s",
                request.wallet,
                chain_res,
                profile_res,
            )
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("failed to fetch full profile")
            return wallet_pb2.FullProfile()

        chain = None if isinstance(chain_res, Exception) else chain_res
        profile = None if isinstance(profile_res, Exception) else profile_res

        last_enriched_at = None
        if profile and profile.last_enriched_at:
            last_enriched_at = profile.last_enriched_at
        elif chain and chain.last_enriched_at:
            last_enriched_at = chain.last_enriched_at

        return wallet_pb2.FullProfile(
            wallet=request.wallet,
            polygon_balance=_str(chain.polygon_balance if chain else None),
            tx_count=_int(chain.tx_count if chain else None),
            profile_status=_str(profile.profile_status if profile else None),
            username=_str(profile.username if profile else None),
            display_name=_str(profile.display_name if profile else None),
            created_at=_ts(profile.created_at if profile else None),
            total_trades=_int(profile.total_trades if profile else None),
            total_volume=_str(profile.total_volume if profile else None),
            total_realized_pnl=_str(profile.total_realized_pnl if profile else None),
            win_rate=_str(profile.win_rate if profile else None),
            avg_pnl_per_trade=_str(profile.avg_pnl_per_trade if profile else None),
            portfolio_value=_str(profile.portfolio_value if profile else None),
            last_enriched_at=_ts(last_enriched_at),
        )


async def run_grpc_server(port: int) -> None:
    server = grpc.aio.server()
    wallet_pb2_grpc.add_WalletServiceServicer_to_server(WalletServicer(), server)
    server.add_insecure_port(f"[::]:{port}")
    await server.start()
    logger.info("gRPC server listening on port %d", port)
    try:
        await server.wait_for_termination()
    finally:
        await server.stop(grace=5)
