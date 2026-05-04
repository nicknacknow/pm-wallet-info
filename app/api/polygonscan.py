"""Polygonscan client for wallet-level chain data."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import httpx

from app.models import WalletChainInfo
from app.settings import (
    HTTP_MAX_RETRIES,
    HTTP_TIMEOUT_SECONDS,
    POLYGONSCAN_API_KEY,
    POLYGONSCAN_BASE_URL,
)


async def _get_json(
    client: httpx.AsyncClient,
    params: dict[str, Any],
) -> dict[str, Any]:
    response = await client.get(POLYGONSCAN_BASE_URL, params=params)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Polygonscan response was not a JSON object")
    return payload


async def _request_with_retries(
    client: httpx.AsyncClient,
    params: dict[str, Any],
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(HTTP_MAX_RETRIES + 1):
        try:
            return await _get_json(client, params)
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc
            if attempt >= HTTP_MAX_RETRIES:
                break
            await asyncio.sleep(2**attempt)
    assert last_error is not None
    raise last_error


def _parse_balance(payload: dict[str, Any]) -> Decimal | None:
    result = payload.get("result")
    if result is None:
        return None
    try:
        return Decimal(str(result))
    except Exception:
        return None


def _parse_tx_count(payload: dict[str, Any]) -> int | None:
    result = payload.get("result")
    if isinstance(result, int):
        return result
    if isinstance(result, str) and result.isdigit():
        return int(result)
    return None


async def fetch_wallet_chain_info(wallet: str) -> WalletChainInfo:
    """Fetch wallet balance and a best-effort transaction count from Polygonscan."""
    headers = {"User-Agent": "pm-wallet-info/0.1"}
    timeout = httpx.Timeout(HTTP_TIMEOUT_SECONDS)
    params_balance = {
        "module": "account",
        "action": "balance",
        "address": wallet,
        "tag": "latest",
        "apikey": POLYGONSCAN_API_KEY,
    }
    params_txcount = {
        "module": "proxy",
        "action": "eth_getTransactionCount",
        "address": wallet,
        "tag": "latest",
        "apikey": POLYGONSCAN_API_KEY,
    }

    async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
        balance_payload = await _request_with_retries(client, params_balance)
        tx_count_payload = await _request_with_retries(client, params_txcount)

    return WalletChainInfo(
        wallet=wallet,
        polygon_balance=_parse_balance(balance_payload),
        tx_count=_parse_tx_count(tx_count_payload),
        last_enriched_at=datetime.now(timezone.utc),
    )