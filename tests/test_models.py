"""Tests for models and pure parsing helpers."""
from decimal import Decimal
from datetime import datetime, timezone, timedelta
import pytest

from app.models import PolymarketProfileInfo
from app.db import is_stale


def _now():
    return datetime.now(timezone.utc)


def test_polymarket_profile_info_fields():
    p = PolymarketProfileInfo(
        wallet="0xabc",
        profile_status="public",
        username="alice",
        display_name="Alice",
        created_at=_now(),
        total_trades=20,
        total_volume=Decimal("500"),
        total_realized_pnl=Decimal("50"),
        win_rate=Decimal("0.6"),
        avg_pnl_per_trade=Decimal("2.5"),
        portfolio_value=Decimal("200"),
        last_enriched_at=_now(),
    )
    assert p.profile_status == "public"
    assert p.username == "alice"
    assert p.total_realized_pnl == Decimal("50")


def test_is_stale_old():
    old = _now() - timedelta(hours=25)
    assert is_stale(old, ttl_hours=24) is True


def test_is_stale_fresh():
    recent = _now() - timedelta(hours=1)
    assert is_stale(recent, ttl_hours=24) is False


def test_is_stale_exactly_at_boundary():
    boundary = _now() - timedelta(hours=24, seconds=1)
    assert is_stale(boundary, ttl_hours=24) is True


def test_is_stale_naive_datetime():
    # naive datetimes should be treated as UTC without raising
    naive = datetime.utcnow() - timedelta(hours=25)
    assert is_stale(naive, ttl_hours=24) is True
