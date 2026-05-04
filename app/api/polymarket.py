"""Polymarket profile client."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import httpx

from app.models import PolymarketProfileInfo
from app.settings import HTTP_MAX_RETRIES, HTTP_TIMEOUT_SECONDS, POLYMARKET_BASE_URL


async def _get_json(
    client: httpx.AsyncClient,
    params: dict[str, Any],
) -> Any:
    response = await client.get(POLYMARKET_BASE_URL, params=params)
    response.raise_for_status()
    return response.json()


async def _request_with_retries(
    client: httpx.AsyncClient,
    params: dict[str, Any],
) -> Any:
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


def _first_profile_entry(payload: Any) -> dict[str, Any] | None:
    if isinstance(payload, list) and payload:
        first_item = payload[0]
        return first_item if isinstance(first_item, dict) else None
    if isinstance(payload, dict):
        if isinstance(payload.get("data"), list) and payload["data"]:
            first_item = payload["data"][0]
            return first_item if isinstance(first_item, dict) else None
        return payload
    return None


def _parse_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


async def fetch_polymarket_profile(wallet: str) -> PolymarketProfileInfo:
    """Fetch a wallet profile from Polymarket's API."""
    timeout = httpx.Timeout(HTTP_TIMEOUT_SECONDS)
    params = {"address": wallet}

    async with httpx.AsyncClient(timeout=timeout) as client:
        payload = await _request_with_retries(client, params)

    entry = _first_profile_entry(payload) or {}
    username = entry.get("username") or entry.get("handle")
    display_name = entry.get("displayName") or entry.get("display_name")

    return PolymarketProfileInfo(
        wallet=wallet,
        username=str(username) if username is not None else None,
        display_name=str(display_name) if display_name is not None else None,
        total_volume=_parse_decimal(entry.get("totalVolume") or entry.get("total_volume")),
        pnl=_parse_decimal(entry.get("pnl") or entry.get("profit")),
        num_trades=entry.get("numTrades") or entry.get("num_trades"),
        last_enriched_at=datetime.now(timezone.utc),
    )