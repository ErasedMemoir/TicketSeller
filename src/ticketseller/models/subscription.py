from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from ticketseller.models.event import EventId
from ticketseller.models.voucher import Voucher, VoucherId


@dataclass
class Subscription(Voucher):
    """Season subscription or commercial package covering multiple events."""

    covered_event_ids: list[EventId] = field(default_factory=list)
    package_name: str | None = None
    discount_rate: Decimal | None = None

    def __init__(
        self,
        id: VoucherId,
        event_id: EventId,
        base_price: Decimal,
        covered_event_ids: list[EventId] | None = None,
        package_name: str | None = None,
        discount_rate: Decimal | None = None,
    ) -> None:
        """Initialize a subscription package."""
        super().__init__(id=id, event_id=event_id, base_price=base_price)
        self.covered_event_ids = covered_event_ids or []
        self.package_name = package_name
        self.discount_rate = discount_rate
        if self.discount_rate is not None and not Decimal("0.00") <= self.discount_rate <= Decimal("1.00"):
            raise ValueError("Subscription discount rate must be between 0 and 1.")
