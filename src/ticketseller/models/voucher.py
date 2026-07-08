from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import NewType

from ticketseller.models.event import EventId


VoucherId = NewType("VoucherId", int)


@dataclass
class Voucher:
    """Base access title for tickets and subscriptions."""

    id: VoucherId
    event_id: EventId
    base_price: Decimal

    def __post_init__(self) -> None:
        """Validate voucher attributes."""
        if self.base_price < Decimal("0.00"):
            raise ValueError("Voucher price cannot be negative.")
