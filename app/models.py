"""Domain models — plain dataclasses, no framework dependency."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any


@dataclass(slots=True)
class WalletChainInfo:
    wallet: str
    polygon_balance: Decimal | None
    tx_count: int | None
    last_enriched_at: datetime


@dataclass(slots=True)
class PolymarketProfileInfo:
    wallet: str
    profile_status: str             # "public" | "private_or_missing" | "error"
    username: str | None
    display_name: str | None
    created_at: datetime | None     # account age — key scoring input
    total_trades: int | None
    total_volume: Decimal | None
    total_realized_pnl: Decimal | None
    win_rate: Decimal | None        # 0.0–1.0
    avg_pnl_per_trade: Decimal | None
    portfolio_value: Decimal | None
    last_enriched_at: datetime


@dataclass(slots=True)
class FullWalletProfile:
    wallet: str
    polygon_balance: Decimal | None
    tx_count: int | None
    profile_status: str | None
    username: str | None
    display_name: str | None
    created_at: datetime | None
    total_trades: int | None
    total_volume: Decimal | None
    total_realized_pnl: Decimal | None
    win_rate: Decimal | None
    avg_pnl_per_trade: Decimal | None
    portfolio_value: Decimal | None
    last_enriched_at: datetime | None
