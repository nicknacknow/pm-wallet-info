"""Polygonscan client — fetches MATIC balance and tx count for a wallet."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from app.models import WalletChainInfo
from app.settings import (
    HTTP_MAX_RETRIES,
    HTTP_TIMEOUT_SECONDS,
    POLYGONSCAN_API_KEY,
    POLYGONSCAN_BASE_URL,
)

logger = logging.getLogger(__name__)


async def _fetch_with_retry(
    client: httpx.AsyncClient,
    params: dict[str, Any],
    label: str,
) -> dict[str, Any]:
    """GET with exponential backoff. Raises on final failure."""
    last: Exception | None = None
    for attempt in range(HTTP_MAX_RETRIES + 1):
        try:
            resp = await client.get(POLYGONSCAN_BASE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, dict):
                raise ValueError(f"Unexpected response shape for {label}: {type(data)}")
            return data
        except (httpx.HTTPError, ValueError) as exc:
            last = exc
            if attempt < HTTP_MAX_RETRIES:
                wait = 2 ** attempt
                logger.warning("polygonscan %s attempt %d failed (%s), retry in %ds", label, attempt, exc, wait)
                await asyncio.sleep(wait)
    raise RuntimeError(f"polygonscan {label} failed after {HTTP_MAX_RETRIES + 1} attempts") from last


def _parse_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return None


def _parse_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        # hex tx count from eth_getTransactionCount
        if value.startswith("0x"):
            try:
                return int(value, 16)
            except ValueError:
                return None
        if value.isdigit():
            return int(value)
    return None


async def fetch_wallet_chain_info(wallet: str) -> WalletChainInfo:
    """Fetch balance and tx count concurrently. Partial results are fine."""
    timeout = httpx.Timeout(HTTP_TIMEOUT_SECONDS)
    headers = {"User-Agent": "pm-wallet-info/1.0"}

    balance_params = {
        "module": "account",
        "action": "balance",
        "address": wallet,
        "tag": "latest",
        "apikey": POLYGONSCAN_API_KEY,
    }
    txcount_params = {
        "module": "proxy",
        "action": "eth_getTransactionCount",
        "address": wallet,
        "tag": "latest",
        "apikey": POLYGONSCAN_API_KEY,
    }

    async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
        balance_res, txcount_res = await asyncio.gather(
            _fetch_with_retry(client, balance_params, "balance"),
            _fetch_with_retry(client, txcount_params, "txcount"),
            return_exceptions=True,
        )

    balance = None
    if not isinstance(balance_res, Exception):
        balance = _parse_decimal(balance_res.get("result"))

    tx_count = None
    if not isinstance(txcount_res, Exception):
        tx_count = _parse_int(txcount_res.get("result"))

    logger.debug("polygonscan wallet=%s balance=%s tx_count=%s", wallet, balance, tx_count)
    return WalletChainInfo(
        wallet=wallet,
        polygon_balance=balance,
        tx_count=tx_count,
        last_enriched_at=datetime.now(timezone.utc),
    )
