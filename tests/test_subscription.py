from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from ticketseller.controllers.ticket_seller import TicketSeller
from ticketseller.dao.ticket_db import TicketDB
from ticketseller.external_services.credit_card_charges import PaymentData
from ticketseller.models.event import Event, EventId
from ticketseller.models.subscription import Subscription
from ticketseller.models.ticket import SeatId
from ticketseller.models.users import Customer, UserId
from ticketseller.models.voucher import VoucherId
from ticketseller.patterns.strategy.standard_pricing import StandardPricing
from ticketseller.patterns.strategy.subscription_pricing import SubscriptionPricing
from test_ticket_seller_controller import FixedPaymentService


class SubscriptionTest(unittest.TestCase):
    """Tests for the use of subscriptions (UC4, RF13)."""

    def setUp(self) -> None:
        """Create an event, a subscription covering it and a controller."""
        self.db = TicketDB()
        self.db.create_event(Event(EventId(1), "Covered", datetime.now(timezone.utc) + timedelta(days=2), 2, Decimal("40.00")))
        self.subscription = Subscription(
            VoucherId(100), EventId(1), Decimal("60.00"), [EventId(1)], "Season Pass", Decimal("0.25")
        )
        self.db.create_subscription(self.subscription)
        self.controller = TicketSeller(
            self.db,
            self.db,
            FixedPaymentService(True),
            StandardPricing(),
            subscription_strategy=SubscriptionPricing(),
            subscription_dao=self.db,
        )
        self.customer = Customer(UserId(1), "Alice Buyer", "alice@example.com")
        self.payment = PaymentData("Alice Buyer", "4111111111111111", 12, 2099, "123")

    def test_total_uses_subscription_strategy_only_with_subscription(self) -> None:
        """Verify the discount is applied only when a subscription is given."""
        tickets = self.db.find_tickets_by_seats(EventId(1), [SeatId("S001")])
        self.assertEqual(Decimal("30.00"), self.controller.calculate_total(tickets, self.subscription))
        self.assertEqual(Decimal("40.00"), self.controller.calculate_total(tickets))

    def test_purchase_with_subscription_is_approved(self) -> None:
        """Verify a purchase with a subscription sells the ticket."""
        result = self.controller.purchase_access_title(
            EventId(1), [SeatId("S001")], self.customer, self.payment, self.subscription
        )
        self.assertTrue(result.approved)
        self.assertEqual("sold", self.db.find_tickets_by_seats(EventId(1), [SeatId("S001")])[0].state.name())

    def test_find_subscription_by_code(self) -> None:
        """Verify subscriptions are found by code and unknown codes are rejected."""
        self.assertEqual(self.subscription, self.controller.find_subscription(VoucherId(100)))
        with self.assertRaises(ValueError):
            self.controller.find_subscription(VoucherId(999))

    def test_subscription_is_saved_in_json(self) -> None:
        """Verify subscriptions are written to and read from the JSON file."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "db.json"
            TicketDB(str(path)).create_subscription(self.subscription)
            restored = TicketDB(str(path)).find_subscription_by_id(VoucherId(100))
        self.assertEqual([EventId(1)], restored.covered_event_ids)
        self.assertEqual(Decimal("0.25"), restored.discount_rate)


if __name__ == "__main__":
    unittest.main()
