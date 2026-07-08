from __future__ import annotations

from decimal import Decimal

from ticketseller.models.subscription import Subscription
from ticketseller.models.ticket import Ticket
from ticketseller.patterns.strategy.pricing_strategy import PricingStrategy, quantize_money


class SubscriptionPricing(PricingStrategy):
    """Pricing strategy that considers subscription event coverage."""

    def calculate_total(self, tickets: list[Ticket], subscription: Subscription | None = None) -> Decimal:
        """Charge only uncovered tickets and apply subscription discount to covered tickets."""
        if subscription is None:
            raise ValueError("Subscription pricing requires a subscription.")
        # Keep a real zero discount distinct from a missing discount.
        discount_rate = subscription.discount_rate if subscription.discount_rate is not None else Decimal("1.00")
        total = Decimal("0.00")
        for ticket in tickets:
            if ticket.event_id in subscription.covered_event_ids:
                total += ticket.base_price * (Decimal("1.00") - discount_rate)
            else:
                total += ticket.base_price
        return quantize_money(total)
