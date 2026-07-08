from __future__ import annotations

from decimal import Decimal

from ticketseller.models.subscription import Subscription
from ticketseller.models.ticket import Ticket
from ticketseller.patterns.strategy.pricing_strategy import PricingStrategy, quantize_money


class GroupPricing(PricingStrategy):
    """Pricing strategy that applies a group discount above a size threshold."""

    def __init__(self, minimum_group_size: int, discount_rate: Decimal) -> None:
        """Initialize group pricing configuration."""
        if minimum_group_size <= 0:
            raise ValueError("Minimum group size must be positive.")
        if not Decimal("0.00") <= discount_rate <= Decimal("1.00"):
            raise ValueError("Discount rate must be between 0 and 1.")
        self.minimum_group_size = minimum_group_size
        self.discount_rate = discount_rate

    def calculate_total(self, tickets: list[Ticket], subscription: Subscription | None = None) -> Decimal:
        """Calculate the total and apply the group discount when eligible."""
        total = sum((ticket.base_price for ticket in tickets), Decimal("0.00"))
        if len(tickets) >= self.minimum_group_size:
            total *= Decimal("1.00") - self.discount_rate
        return quantize_money(total)
