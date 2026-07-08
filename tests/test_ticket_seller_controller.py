from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from ticketseller.controllers.ticket_seller import TicketSeller
from ticketseller.dao.ticket_db import TicketDB
from ticketseller.external_services.credit_card_charges import PaymentData, PaymentResult
from ticketseller.models.event import Event, EventId
from ticketseller.models.ticket import SeatId
from ticketseller.models.users import Clerk, Customer, UserId
from ticketseller.patterns.strategy.standard_pricing import StandardPricing


class FixedPaymentService:
    """Deterministic payment service for controller tests."""

    def __init__(self, approved: bool) -> None:
        """Initialize deterministic approval behavior."""
        self.approved = approved

    def process_payment(self, payment_data: PaymentData, amount: Decimal) -> PaymentResult:
        """Return a fixed payment result."""
        if self.approved:
            return PaymentResult(True, "TX-TEST")
        return PaymentResult(False, error_message="Declined")


class TicketSellerControllerTest(unittest.TestCase):
    """Unit tests for controller orchestration."""

    def setUp(self) -> None:
        """Create a database, event, and customer for each test."""
        self.db = TicketDB()
        self.event = Event(EventId(1), "Future Concert", datetime.now(timezone.utc) + timedelta(days=3), 3, Decimal("25.00"))
        self.db.create_event(self.event)
        self.customer = Customer(UserId(1), "Alice Buyer", "alice@example.com")
        self.payment = PaymentData("Alice Buyer", "4111111111111111", 12, 2099, "123")

    def test_successful_purchase_sells_ticket(self) -> None:
        """Verify approved payment confirms ticket sale."""
        controller = TicketSeller(self.db, self.db, FixedPaymentService(True), StandardPricing())
        result = controller.purchase_access_title(EventId(1), [SeatId("S001")], self.customer, self.payment)
        ticket = self.db.find_tickets_by_seats(EventId(1), [SeatId("S001")])[0]
        self.assertTrue(result.approved)
        self.assertEqual("sold", ticket.state.name())

    def test_declined_purchase_releases_ticket(self) -> None:
        """Verify declined payment releases the locked ticket."""
        controller = TicketSeller(self.db, self.db, FixedPaymentService(False), StandardPricing())
        result = controller.purchase_access_title(EventId(1), [SeatId("S002")], self.customer, self.payment)
        ticket = self.db.find_tickets_by_seats(EventId(1), [SeatId("S002")])[0]
        self.assertFalse(result.approved)
        self.assertEqual("available", ticket.state.name())

    def test_duplicate_seat_selection_is_rejected(self) -> None:
        """Verify duplicate seat requests are rejected by availability checks."""
        controller = TicketSeller(self.db, self.db, FixedPaymentService(True), StandardPricing())

        self.assertFalse(controller.check_availability(EventId(1), [SeatId("S001"), SeatId("S001")]))

        with self.assertRaises(ValueError):
            controller.reserve_seats(EventId(1), [SeatId("S001"), SeatId("S001")], self.customer)

    def test_clerk_can_create_event(self) -> None:
        """Verify authorized clerk event creation."""
        controller = TicketSeller(self.db, self.db, FixedPaymentService(True), StandardPricing())
        clerk = Clerk(UserId(10), "Admin Clerk", "clerk@example.com", "EMP-1")
        event = Event(EventId(2), "Created Event", datetime.now(timezone.utc) + timedelta(days=4), 1, Decimal("12.00"))

        created = controller.create_event(clerk, event)

        self.assertEqual("Created Event", created.name)

    def test_past_event_creation_is_rejected(self) -> None:
        """Verify controller rejects past events."""
        controller = TicketSeller(self.db, self.db, FixedPaymentService(True), StandardPricing())
        clerk = Clerk(UserId(10), "Admin Clerk", "clerk@example.com", "EMP-1")
        event = Event(EventId(3), "Past Event", datetime.now(timezone.utc) - timedelta(days=1), 1, Decimal("12.00"))

        with self.assertRaises(ValueError):
            controller.create_event(clerk, event)

    def test_expired_reservation_is_released(self) -> None:
        """Verify expired locked tickets are released."""
        controller = TicketSeller(self.db, self.db, FixedPaymentService(True), StandardPricing())
        ticket = self.db.find_tickets_by_seats(EventId(1), [SeatId("S001")])[0]
        ticket.reserve(self.customer)
        ticket.locked_at = datetime.now(timezone.utc) - TicketSeller.reservation_timeout - timedelta(seconds=1)
        self.db.save_ticket(ticket)

        released = controller.release_expired_reservations(EventId(1))

        self.assertEqual(1, len(released))
        self.assertEqual("available", ticket.state.name())

    def test_unauthorized_clerk_is_rejected(self) -> None:
        """Verify administrative actions require a valid clerk."""
        controller = TicketSeller(self.db, self.db, FixedPaymentService(True), StandardPricing())
        invalid_clerk = Customer(UserId(20), "Not Clerk", "customer@example.com")
        event = Event(EventId(4), "Rejected Event", datetime.now(timezone.utc) + timedelta(days=4), 1, Decimal("12.00"))

        with self.assertRaises(PermissionError):
            controller.create_event(invalid_clerk, event)

    def test_empty_seat_purchase_is_rejected(self) -> None:
        """Verify purchase requires at least one selected seat."""
        controller = TicketSeller(self.db, self.db, FixedPaymentService(True), StandardPricing())

        with self.assertRaises(ValueError):
            controller.purchase_access_title(EventId(1), [], self.customer, self.payment)


if __name__ == "__main__":
    unittest.main()
