"""Domain models for wallet enrichment and persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass(slots=True)
class WalletChainInfo:
    wallet: str
    polygon_balance: Optional[Decimal]
    tx_count: Optional[int]
    last_enriched_at: datetime


@dataclass(slots=True)
class PolymarketProfileInfo:
    wallet: str
    username: Optional[str]
    display_name: Optional[str]
    total_volume: Optional[Decimal]
    pnl: Optional[Decimal]
    num_trades: Optional[int]
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