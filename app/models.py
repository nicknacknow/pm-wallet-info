"""Domain models — plain dataclasses, no framework dependency."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(slots=True)
class PolymarketProfileInfo:
    wallet: str
    profile_status: str             # "public" | "private_or_missing" | "error"
    username: str | None
    display_name: str | None
    created_at: datetime | None
    total_trades: int | None
    total_volume: Decimal | None
    total_realized_pnl: Decimal | None
    win_rate: Decimal | None
    avg_pnl_per_trade: Decimal | None
    portfolio_value: Decimal | None
    last_enriched_at: datetime
