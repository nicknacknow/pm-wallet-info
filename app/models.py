"""Domain models for wallet enrichment and persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional


@dataclass(slots=True)
class WalletChainInfo:
    wallet: str
    polygon_balance: Optional[Decimal]
    tx_count: Optional[int]
    last_enriched_at: datetime


@dataclass(slots=True)
class PolymarketProfileInfo:
    wallet: str
    profile_status: str
    username: Optional[str]
    display_name: Optional[str]
    total_volume: Optional[Decimal]
    pnl: Optional[Decimal]
    num_trades: Optional[int]
    stats_status: str
    positions_status: str
    profile_created_at: Optional[datetime]
    proxy_wallet: Optional[str]
    profile_image: Optional[str]
    display_username_public: Optional[bool]
    bio: Optional[str]
    pseudonym: Optional[str]
    x_username: Optional[str]
    verified_badge: Optional[bool]
    profile_payload: dict[str, Any] | None
    positions_count: Optional[int]
    active_positions_count: Optional[int]
    positions_current_value: Optional[Decimal]
    positions_cash_pnl: Optional[Decimal]
    positions_realized_pnl: Optional[Decimal]
    positions_total_bought: Optional[Decimal]
    positions_initial_value: Optional[Decimal]
    positions_payload: dict[str, Any] | list[dict[str, Any]] | None
    last_enriched_at: datetime


@dataclass(slots=True)
class FullWalletProfile:
    wallet: str
    polygon_balance: Optional[Decimal]
    tx_count: Optional[int]
    username: Optional[str]
    display_name: Optional[str]
    total_volume: Optional[Decimal]
    pnl: Optional[Decimal]
    num_trades: Optional[int]
    last_enriched_at: Optional[datetime]