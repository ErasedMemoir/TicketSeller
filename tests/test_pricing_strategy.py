from __future__ import annotations

import unittest
from decimal import Decimal

from ticketseller.models.event import EventId
from ticketseller.models.subscription import Subscription
from ticketseller.models.ticket import SeatId, Ticket
from ticketseller.models.voucher import VoucherId
from ticketseller.patterns.strategy.group_pricing import GroupPricing
from ticketseller.patterns.strategy.standard_pricing import StandardPricing
from ticketseller.patterns.strategy.subscription_pricing import SubscriptionPricing


class PricingStrategyTest(unittest.TestCase):
    """Unit tests for the pricing Strategy pattern."""

    def setUp(self) -> None:
        """Create sample tickets for strategy calculations."""
        self.tickets = [
            Ticket(VoucherId(1), EventId(1), Decimal("10.00"), SeatId("A1")),
            Ticket(VoucherId(2), EventId(1), Decimal("20.00"), SeatId("A2")),
            Ticket(VoucherId(3), EventId(2), Decimal("30.00"), SeatId("B1")),
        ]

    def test_standard_pricing_sums_base_prices(self) -> None:
        """Verify standard pricing applies no discount."""
        self.assertEqual(Decimal("60.00"), StandardPricing().calculate_total(self.tickets))

    def test_group_pricing_applies_threshold_discount(self) -> None:
        """Verify group discount is applied only above the configured threshold."""
        strategy = GroupPricing(minimum_group_size=3, discount_rate=Decimal("0.10"))
        self.assertEqual(Decimal("54.00"), strategy.calculate_total(self.tickets))

    def test_subscription_pricing_discounts_covered_events(self) -> None:
        """Verify subscription pricing discounts only covered event tickets."""
        subscription = Subscription(
            VoucherId(99),
            EventId(1),
            Decimal("100.00"),
            covered_event_ids=[EventId(1)],
            discount_rate=Decimal("1.00"),
        )
        self.assertEqual(Decimal("30.00"), SubscriptionPricing().calculate_total(self.tickets, subscription))

    def test_subscription_zero_discount_keeps_covered_ticket_price(self) -> None:
        """Verify zero discount does not become a full discount."""
        subscription = Subscription(
            VoucherId(99),
            EventId(1),
            Decimal("100.00"),
            covered_event_ids=[EventId(1)],
            discount_rate=Decimal("0.00"),
        )

        self.assertEqual(Decimal("60.00"), SubscriptionPricing().calculate_total(self.tickets, subscription))

    def test_group_pricing_below_threshold_has_no_discount(self) -> None:
        """Verify group pricing does not discount small purchases."""
        strategy = GroupPricing(minimum_group_size=5, discount_rate=Decimal("0.10"))

        self.assertEqual(Decimal("60.00"), strategy.calculate_total(self.tickets))

    def test_subscription_pricing_requires_subscription(self) -> None:
        """Verify subscription pricing requires subscription data."""
        with self.assertRaises(ValueError):
            SubscriptionPricing().calculate_total(self.tickets)


if __name__ == "__main__":
    unittest.main()
