"""Polymarket profile + positions client."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from app.models import PolymarketProfileInfo
from app.settings import (
    HTTP_MAX_RETRIES,
    HTTP_TIMEOUT_SECONDS,
    POLYMARKET_PROFILE_URL,
    POLYMARKET_CLOSED_POS_URL,
    POLYMARKET_VALUE_URL,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

async def _get_with_retry(
    client: httpx.AsyncClient,
    url: str,
    params: dict[str, Any],
    label: str,
) -> Any:
    last: Exception | None = None
    for attempt in range(HTTP_MAX_RETRIES + 1):
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise  # don't retry 404s
            last = exc
        except (httpx.HTTPError, ValueError) as exc:
            last = exc
        if attempt < HTTP_MAX_RETRIES:
            wait = 2 ** attempt
            logger.warning("polymarket %s attempt %d failed, retry in %ds", label, attempt, wait)
            await asyncio.sleep(wait)
    raise RuntimeError(f"polymarket {label} failed after {HTTP_MAX_RETRIES + 1} attempts") from last


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def _dec(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return None


def _sum_field(entries: list[dict[str, Any]], field: str) -> Decimal | None:
    total, found = Decimal("0"), False
    for e in entries:
        v = _dec(e.get(field))
        if v is not None:
            total += v
            found = True
    return total if found else None


def _active_count(entries: list[dict[str, Any]]) -> int | None:
    seen = False
    count = 0
    for e in entries:
        v = _dec(e.get("currentValue"))
        if v is not None:
            seen = True
            if v > 0:
                count += 1
    return count if seen else None


def _extract_profile_entry(payload: Any) -> dict[str, Any]:
    """Normalise whatever shape the profile endpoint returns to a single dict."""
    if isinstance(payload, list) and payload:
        first = payload[0]
        return first if isinstance(first, dict) else {}
    if isinstance(payload, dict):
        if isinstance(payload.get("data"), list) and payload["data"]:
            first = payload["data"][0]
            return first if isinstance(first, dict) else {}
        return payload
    return {}


def _extract_positions(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [p for p in payload if isinstance(p, dict)]
    if isinstance(payload, dict):
        for key in ("data", "positions", "results"):
            v = payload.get(key)
            if isinstance(v, list):
                return [p for p in v if isinstance(p, dict)]
    return []


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Main fetch
# ---------------------------------------------------------------------------

async def fetch_polymarket_profile(wallet: str) -> PolymarketProfileInfo:
    timeout = httpx.Timeout(HTTP_TIMEOUT_SECONDS)
    profile_params        = {"address": wallet}
    closed_pos_params     = {"user": wallet, "limit": 500, "offset": 0}
    value_params          = {"user": wallet}

    async with httpx.AsyncClient(timeout=timeout) as client:
        profile_res, closed_res, value_res = await asyncio.gather(
            _get_with_retry(client, POLYMARKET_PROFILE_URL,        profile_params,    "profile"),
            _get_with_retry(client, POLYMARKET_CLOSED_POS_URL,     closed_pos_params, "closed-positions"),
            _get_with_retry(client, POLYMARKET_VALUE_URL,          value_params,      "value"),
            return_exceptions=True,
        )

    # --- profile ------------------------------------------------------------
    if isinstance(profile_res, Exception):
        is_404 = (
            isinstance(profile_res, httpx.HTTPStatusError)
            and profile_res.response.status_code == 404
        )
        profile_status = "private_or_missing" if is_404 else "error"
        logger.warning("profile fetch failed wallet=%s status=%s", wallet, profile_status)
        entry: dict[str, Any] = {}
    else:
        profile_status = "public"
        entry = _extract_profile_entry(profile_res)

    # correct field names from actual API response
    username     = entry.get("name")        # "kai03111"
    display_name = entry.get("pseudonym")   # "Costly-Preparation"
    created_at   = _parse_dt(entry.get("createdAt"))

    # --- closed positions ---------------------------------------------------
    closed: list[dict[str, Any]] = []
    if not isinstance(closed_res, Exception):
        closed = _extract_positions(closed_res)

    total_trades      = len(closed) if not isinstance(closed_res, Exception) else None
    total_volume      = _sum_field(closed, "totalBought")
    total_realized_pnl = _sum_field(closed, "realizedPnl")
    wins              = sum(1 for p in closed if (_dec(p.get("realizedPnl")) or Decimal(0)) > 0)
    win_rate          = Decimal(wins) / Decimal(total_trades) if total_trades else None
    avg_pnl_per_trade = (
        total_realized_pnl / Decimal(total_trades)
        if total_realized_pnl is not None and total_trades
        else None
    )

    # --- current value ------------------------------------------------------
    portfolio_value = None
    if not isinstance(value_res, Exception) and isinstance(value_res, list) and value_res:
        portfolio_value = _dec(value_res[0].get("value"))

    return PolymarketProfileInfo(
        wallet=wallet,
        profile_status=profile_status,
        username=username,
        display_name=display_name,
        created_at=created_at,
        total_trades=total_trades,
        total_volume=total_volume,
        total_realized_pnl=total_realized_pnl,
        win_rate=win_rate,
        avg_pnl_per_trade=avg_pnl_per_trade,
        portfolio_value=portfolio_value,
        last_enriched_at=datetime.now(timezone.utc),
    )
