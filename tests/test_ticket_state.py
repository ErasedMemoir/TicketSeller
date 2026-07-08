from __future__ import annotations

import unittest
from decimal import Decimal

from ticketseller.models.event import EventId
from ticketseller.models.ticket import SeatId, Ticket
from ticketseller.models.users import Customer, UserId
from ticketseller.models.voucher import VoucherId


class TicketStateTest(unittest.TestCase):
    """Unit tests for the ticket State pattern."""

    def setUp(self) -> None:
        """Create a fresh ticket and customer for each test."""
        self.customer = Customer(UserId(1), "Alice Buyer", "alice@example.com")
        self.ticket = Ticket(VoucherId(1), EventId(1), Decimal("20.00"), SeatId("A1"))

    def test_ticket_lifecycle_available_locked_sold(self) -> None:
        """Verify valid state transitions from available to sold."""
        self.assertTrue(self.ticket.is_available())
        self.ticket.reserve(self.customer)
        self.assertEqual("locked", self.ticket.state.name())
        self.assertFalse(self.ticket.is_available())
        self.ticket.confirm_sale(self.customer)
        self.assertEqual("sold", self.ticket.state.name())
        self.assertEqual(self.customer, self.ticket.owner)

    def test_locked_ticket_can_be_cancelled(self) -> None:
        """Verify locked tickets return to available state after cancellation."""
        self.ticket.reserve(self.customer)
        self.ticket.cancel()
        self.assertEqual("available", self.ticket.state.name())
        self.assertIsNone(self.ticket.owner)

    def test_invalid_transitions_raise_errors(self) -> None:
        """Verify invalid lifecycle operations are rejected."""
        with self.assertRaises(ValueError):
            self.ticket.confirm_sale(self.customer)
        self.ticket.reserve(self.customer)
        with self.assertRaises(ValueError):
            self.ticket.reserve(self.customer)
        self.ticket.confirm_sale(self.customer)
        with self.assertRaises(ValueError):
            self.ticket.cancel()


if __name__ == "__main__":
    unittest.main()
