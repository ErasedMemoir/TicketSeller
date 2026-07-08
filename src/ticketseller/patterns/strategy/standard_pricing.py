from __future__ import annotations

from decimal import Decimal

from ticketseller.models.subscription import Subscription
from ticketseller.models.ticket import Ticket
from ticketseller.patterns.strategy.pricing_strategy import PricingStrategy, quantize_money


class StandardPricing(PricingStrategy):
    """Pricing strategy for regular ticket sales without discounts."""

    def calculate_total(self, tickets: list[Ticket], subscription: Subscription | None = None) -> Decimal:
        """Return the sum of all ticket base prices."""
        return quantize_money(sum((ticket.base_price for ticket in tickets), Decimal("0.00")))
