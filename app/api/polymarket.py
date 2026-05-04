"""Polymarket profile client."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import httpx

from app.models import PolymarketProfileInfo
from app.settings import (
    HTTP_MAX_RETRIES,
    HTTP_TIMEOUT_SECONDS,
    POLYMARKET_BASE_URL,
    POLYMARKET_DATA_BASE_URL,
)


async def _get_json(
    client: httpx.AsyncClient,
    url: str,
    params: dict[str, Any],
) -> Any:
    response = await client.get(url, params=params)
    response.raise_for_status()
    return response.json()


async def _request_with_retries(
    client: httpx.AsyncClient,
    url: str,
    params: dict[str, Any],
) -> Any:
    last_error: Exception | None = None
    for attempt in range(HTTP_MAX_RETRIES + 1):
        try:
            return await _get_json(client, url, params)
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


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _coerce_position_entries(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("data", "positions", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return [payload]
    return []


def _sum_decimal(entries: list[dict[str, Any]], field: str) -> Decimal | None:
    total = Decimal("0")
    has_value = False

    for entry in entries:
        value = entry.get(field)
        if value is None:
            continue
        try:
            total += Decimal(str(value))
            has_value = True
        except Exception:
            continue

    return total if has_value else None


def _count_active_positions(entries: list[dict[str, Any]]) -> int | None:
    active_count = 0
    seen_any_value = False

    for entry in entries:
        current_value = _parse_decimal(entry.get("currentValue"))
        if current_value is None:
            continue
        seen_any_value = True
        if current_value != 0:
            active_count += 1

    return active_count if seen_any_value else None


async def fetch_polymarket_profile(wallet: str) -> PolymarketProfileInfo:
    """Fetch a wallet profile from Polymarket's API."""
    timeout = httpx.Timeout(HTTP_TIMEOUT_SECONDS)
    params = {"address": wallet}
    positions_url = f"{POLYMARKET_DATA_BASE_URL.rstrip('/')}/positions"
    positions_params = {
        "user": wallet,
        "limit": 500,
        "offset": 0,
        "sortBy": "CURRENT",
        "sortDirection": "DESC",
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        profile_task = _request_with_retries(client, POLYMARKET_BASE_URL, params)
        positions_task = _request_with_retries(client, positions_url, positions_params)

        profile_result, positions_result = await asyncio.gather(
            profile_task,
            positions_task,
            return_exceptions=True,
        )

    positions_entries = _coerce_position_entries(positions_result) if not isinstance(positions_result, Exception) else []
    positions_count = len(positions_entries) if not isinstance(positions_result, Exception) else None
    active_positions_count = _count_active_positions(positions_entries)
    positions_current_value = _sum_decimal(positions_entries, "currentValue")
    positions_cash_pnl = _sum_decimal(positions_entries, "cashPnl")
    positions_realized_pnl = _sum_decimal(positions_entries, "realizedPnl")
    positions_total_bought = _sum_decimal(positions_entries, "totalBought")
    positions_initial_value = _sum_decimal(positions_entries, "initialValue")
    positions_status = "complete" if positions_entries else "no_positions" if not isinstance(positions_result, Exception) else "unknown"

    profile_payload = None if isinstance(profile_result, Exception) else profile_result
    entry = _first_profile_entry(profile_payload) or {}

    if isinstance(profile_result, Exception):
        if isinstance(profile_result, httpx.HTTPStatusError) and profile_result.response.status_code == 404:
            profile_status = "private_or_missing"
        else:
            profile_status = "unknown"
        username = None
        display_name = None
        profile_created_at = None
        proxy_wallet = None
        profile_image = None
        display_username_public = None
        bio = None
        pseudonym = None
        x_username = None
        verified_badge = None
    else:
        profile_status = "public"
        username = entry.get("xUsername") or entry.get("username") or entry.get("handle") or entry.get("pseudonym") or entry.get("name")
        display_name = entry.get("name") or entry.get("displayName") or entry.get("display_name") or entry.get("pseudonym")
        profile_created_at = _parse_datetime(entry.get("createdAt"))
        proxy_wallet = str(entry.get("proxyWallet")) if entry.get("proxyWallet") is not None else None
        profile_image = str(entry.get("profileImage")) if entry.get("profileImage") is not None else None
        display_username_public = entry.get("displayUsernamePublic")
        bio = str(entry.get("bio")) if entry.get("bio") is not None else None
        pseudonym = str(entry.get("pseudonym")) if entry.get("pseudonym") is not None else None
        x_username = str(entry.get("xUsername")) if entry.get("xUsername") is not None else None
        verified_badge = entry.get("verifiedBadge")

    total_volume = _parse_decimal(
        entry.get("totalVolume")
        or entry.get("total_volume")
        or entry.get("volume")
        or entry.get("volume24hr")
        or entry.get("value")
    )
    if total_volume is None:
        total_volume = positions_total_bought

    return PolymarketProfileInfo(
        wallet=wallet,
        profile_status=profile_status,
        username=str(username) if username is not None else None,
        display_name=str(display_name) if display_name is not None else None,
        total_volume=total_volume,
        pnl=positions_cash_pnl,
        num_trades=entry.get("numTrades") or entry.get("num_trades") or entry.get("predictions"),
        stats_status="complete" if not isinstance(positions_result, Exception) else "unknown",
        positions_status=positions_status,
        profile_created_at=profile_created_at,
        proxy_wallet=proxy_wallet,
        profile_image=profile_image,
        display_username_public=display_username_public,
        bio=bio,
        pseudonym=pseudonym,
        x_username=x_username,
        verified_badge=verified_badge,
        profile_payload=entry if profile_status == "public" else None,
        positions_count=positions_count,
        active_positions_count=active_positions_count,
        positions_current_value=positions_current_value,
        positions_cash_pnl=positions_cash_pnl,
        positions_realized_pnl=positions_realized_pnl,
        positions_total_bought=positions_total_bought,
        positions_initial_value=positions_initial_value,
        positions_payload=positions_entries if not isinstance(positions_result, Exception) else None,
        last_enriched_at=datetime.now(timezone.utc),
    )

