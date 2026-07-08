from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import NewType


EventId = NewType("EventId", int)


@dataclass
class Event:
    """Sellable event managed by the TicketSeller system."""

    id: EventId
    name: str
    date: datetime
    capacity: int
    base_price: Decimal
    venue_name: str | None = None
    description: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate event business constraints."""
        if not self.name.strip():
            raise ValueError("Event name cannot be empty.")
        if self.capacity <= 0:
            raise ValueError("Event capacity must be positive.")
        if self.base_price < Decimal("0.00"):
            raise ValueError("Base price cannot be negative.")
