from __future__ import annotations

import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from ticketseller.controllers.ticket_seller import TicketSeller
from ticketseller.dao.ticket_db import TicketDB
from ticketseller.external_services.credit_card_charges import CreditCardCharges, PaymentData, PaymentResult
from ticketseller.models.event import Event, EventId
from ticketseller.models.subscription import Subscription
from ticketseller.models.ticket import SeatId, Ticket
from ticketseller.models.users import Clerk, Customer, UserId
from ticketseller.models.voucher import VoucherId
from ticketseller.patterns.strategy.group_pricing import GroupPricing
from ticketseller.patterns.strategy.standard_pricing import StandardPricing
from ticketseller.patterns.strategy.subscription_pricing import SubscriptionPricing
from test_ticket_seller_controller import FixedPaymentService


class RecordingPaymentService(FixedPaymentService):
    """Payment service spy recording the requested amounts."""

    def __init__(self, approved: bool) -> None:
        """Initialize the spy."""
        super().__init__(approved)
        self.amounts: list[Decimal] = []

    def process_payment(self, payment_data: PaymentData, amount: Decimal) -> PaymentResult:
        """Record the amount and return a fixed result."""
        self.amounts.append(amount)
        return super().process_payment(payment_data, amount)


class RequirementsCoverageTest(unittest.TestCase):
    """Controller-level tests covering functional requirements RF1-RF13."""

    def setUp(self) -> None:
        """Create a database with one future event of three seats."""
        self.now = datetime.now(timezone.utc)
        self.db = TicketDB()
        self.db.create_event(Event(EventId(1), "Future Concert", self.now + timedelta(days=3), 3, Decimal("25.00")))
        self.customer = Customer(UserId(1), "Alice Buyer", "alice@example.com")
        self.other = Customer(UserId(2), "Bob Buyer", "bob@example.com")
        self.clerk = Clerk(UserId(10), "Admin Clerk", "clerk@example.com", "EMP-1")
        self.payment = PaymentData("Alice Buyer", "4111111111111111", 12, 2099, "123")
        self.spy = RecordingPaymentService(True)
        self.controller = TicketSeller(self.db, self.db, self.spy, StandardPricing())

    def _ticket(self, seat: str) -> Ticket:
        return self.db.find_tickets_by_seats(EventId(1), [SeatId(seat)])[0]

    def test_rf1_search_future_events_excludes_past_events(self) -> None:
        """RF1: only future events are returned, sorted by date."""
        self.db.create_event(Event(EventId(2), "Past", self.now - timedelta(days=1), 1, Decimal("5.00")))
        self.db.create_event(Event(EventId(3), "Sooner", self.now + timedelta(days=1), 1, Decimal("5.00")))

        names = [event.name for event in self.controller.search_future_events()]

        self.assertEqual(["Sooner", "Future Concert"], names)

    def test_rf2_seating_map_lists_every_seat_with_state(self) -> None:
        """RF2: the seating map contains all seats and their states."""
        self.controller.reserve_seats(EventId(1), [SeatId("S002")], self.customer)

        seating = {str(t.seat_id): t.state.name() for t in self.controller.get_seating_map(EventId(1))}

        self.assertEqual({"S001": "available", "S002": "locked", "S003": "available"}, seating)

    def test_rf3_check_availability_reports_locked_seats(self) -> None:
        """RF3: availability is True for free seats and False when any seat is locked."""
        self.assertTrue(self.controller.check_availability(EventId(1), [SeatId("S001"), SeatId("S002")]))
        self.controller.reserve_seats(EventId(1), [SeatId("S002")], self.customer)
        self.assertFalse(self.controller.check_availability(EventId(1), [SeatId("S001"), SeatId("S002")]))

    def test_rf4_reserve_locks_seats_for_customer(self) -> None:
        """RF4: reservation locks the seats, records owner and lock time, blocks others."""
        self.controller.reserve_seats(EventId(1), [SeatId("S001")], self.customer)
        ticket = self._ticket("S001")

        self.assertEqual("locked", ticket.state.name())
        self.assertEqual(self.customer, ticket.owner)
        self.assertIsNotNone(ticket.locked_at)
        with self.assertRaises(ValueError):
            self.controller.reserve_seats(EventId(1), [SeatId("S001")], self.other)

    def test_rf5_runtime_strategy_change_applies_group_discount(self) -> None:
        """RF5: totals follow the active strategy and stay Decimal with 2 decimals."""
        self.controller.set_pricing_strategy(GroupPricing(minimum_group_size=3, discount_rate=Decimal("0.10")))

        self.controller.purchase_access_title(EventId(1), [SeatId("S001"), SeatId("S002"), SeatId("S003")], self.customer, self.payment)

        self.assertEqual([Decimal("67.50")], self.spy.amounts)
        self.assertEqual(-2, self.spy.amounts[0].as_tuple().exponent)

    def test_rf6_payment_service_receives_computed_total(self) -> None:
        """RF6: the payment request carries the computed total."""
        self.controller.purchase_access_title(EventId(1), [SeatId("S001"), SeatId("S002")], self.customer, self.payment)

        self.assertEqual([Decimal("50.00")], self.spy.amounts)

    def test_rf7_approved_payment_assigns_owner(self) -> None:
        """RF7: sold tickets belong to the paying customer."""
        self.controller.purchase_access_title(EventId(1), [SeatId("S001")], self.customer, self.payment)

        self.assertEqual("sold", self._ticket("S001").state.name())
        self.assertEqual(self.customer, self._ticket("S001").owner)
        self.assertIsNone(self._ticket("S001").locked_at)

    def test_rf9_rnf7_timeout_boundary(self) -> None:
        """RF9/RNF7: locks younger than the timeout survive, older ones are released."""
        self.controller.reserve_seats(EventId(1), [SeatId("S001"), SeatId("S002")], self.customer)
        self._ticket("S001").locked_at = self.now - TicketSeller.reservation_timeout + timedelta(minutes=1)
        self._ticket("S002").locked_at = self.now - TicketSeller.reservation_timeout - timedelta(seconds=1)

        released = self.controller.release_expired_reservations()

        self.assertEqual(["S002"], [str(t.seat_id) for t in released])
        self.assertEqual("locked", self._ticket("S001").state.name())
        self.assertEqual("available", self._ticket("S002").state.name())

    def test_rf9_seating_map_releases_expired_locks(self) -> None:
        """RF9: consulting the seating map releases expired reservations."""
        self.controller.reserve_seats(EventId(1), [SeatId("S001")], self.customer)
        self._ticket("S001").locked_at = self.now - timedelta(hours=1)

        seating = {str(t.seat_id): t.state.name() for t in self.controller.get_seating_map(EventId(1))}

        self.assertEqual("available", seating["S001"])

    def test_rf10_clerk_creates_event_with_seating_map(self) -> None:
        """RF10: a created event is browsable and has capacity seats."""
        self.controller.create_event(self.clerk, Event(EventId(2), "New", self.now + timedelta(days=5), 4, Decimal("10.00")))

        self.assertIn("New", [e.name for e in self.controller.search_future_events()])
        self.assertEqual(4, len(self.controller.get_seating_map(EventId(2))))

    def test_rf11_clerk_updates_event(self) -> None:
        """RF11: clerk updates are persisted; customers and past dates are rejected."""
        updated = Event(EventId(1), "Renamed", self.now + timedelta(days=4), 5, Decimal("25.00"))

        self.controller.update_event(self.clerk, updated)

        self.assertEqual("Renamed", self.controller.find_event_by_id(EventId(1)).name)
        self.assertEqual(5, len(self.controller.get_seating_map(EventId(1))))
        with self.assertRaises(PermissionError):
            self.controller.update_event(self.customer, updated)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            self.controller.update_event(self.clerk, Event(EventId(1), "Past", self.now - timedelta(days=1), 5, Decimal("25.00")))

    def test_rf12_clerk_deletes_event(self) -> None:
        """RF12: clerk deletes unsold events; customers cannot; sold events are protected."""
        with self.assertRaises(PermissionError):
            self.controller.delete_event(self.customer, EventId(1))  # type: ignore[arg-type]
        self.controller.delete_event(self.clerk, EventId(1))
        self.assertIsNone(self.controller.find_event_by_id(EventId(1)))

        self.controller.create_event(self.clerk, Event(EventId(2), "Sold", self.now + timedelta(days=2), 1, Decimal("5.00")))
        self.controller.purchase_access_title(EventId(2), [SeatId("S001")], self.customer, self.payment)
        with self.assertRaises(ValueError):
            self.controller.delete_event(self.clerk, EventId(2))

    def test_rf13_subscription_purchase_charges_discounted_amount(self) -> None:
        """RF13: buying through the controller with a subscription charges the discounted total."""
        self.db.create_event(Event(EventId(2), "Uncovered", self.now + timedelta(days=3), 1, Decimal("40.00")))
        subscription = Subscription(VoucherId(99), EventId(1), Decimal("100.00"), covered_event_ids=[EventId(1)], discount_rate=Decimal("0.20"))
        self.controller.set_pricing_strategy(SubscriptionPricing())

        self.controller.purchase_access_title(EventId(1), [SeatId("S001")], self.customer, self.payment, subscription)
        self.controller.purchase_access_title(EventId(2), [SeatId("S001")], self.customer, self.payment, subscription)

        self.assertEqual([Decimal("20.00"), Decimal("40.00")], self.spy.amounts)

    def test_rnf3_concurrent_reservations_allow_one_winner(self) -> None:
        """RNF3: concurrent threads cannot double-reserve the same seat."""
        winners: list[int] = []
        barrier = threading.Barrier(20)

        def worker(index: int) -> None:
            barrier.wait()
            try:
                self.controller.reserve_seats(EventId(1), [SeatId("S001")], self.customer)
                winners.append(index)
            except ValueError:
                pass

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(1, len(winners))

    def test_rnf5_json_roundtrip_preserves_states_owner_and_lock_time(self) -> None:
        """RNF5: locked and sold tickets are rebuilt with state, owner and locked_at."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "db.json"
            db = TicketDB(str(path))
            db.create_event(Event(EventId(1), "Stored", self.now + timedelta(days=1), 2, Decimal("10.00")))
            controller = TicketSeller(db, db, FixedPaymentService(True), StandardPricing())
            controller.reserve_seats(EventId(1), [SeatId("S001")], self.customer)
            controller.purchase_access_title(EventId(1), [SeatId("S002")], self.other, self.payment)
            locked_at = db.find_tickets_by_seats(EventId(1), [SeatId("S001")])[0].locked_at

            restored = {str(t.seat_id): t for t in TicketDB(str(path)).find_tickets_by_event(EventId(1))}

            self.assertEqual("locked", restored["S001"].state.name())
            self.assertEqual(locked_at, restored["S001"].locked_at)
            self.assertEqual(self.customer, restored["S001"].owner)
            self.assertEqual("sold", restored["S002"].state.name())
            self.assertEqual(self.other, restored["S002"].owner)

    def test_sold_state_is_terminal(self) -> None:
        """State: every operation on a sold ticket is rejected."""
        ticket = Ticket(VoucherId(1), EventId(1), Decimal("10.00"), SeatId("A1"))
        ticket.reserve(self.customer)
        ticket.confirm_sale(self.customer)
        for operation in (lambda: ticket.reserve(self.other), ticket.cancel, lambda: ticket.confirm_sale(self.other)):
            with self.assertRaises(ValueError):
                operation()
        self.assertEqual("sold", ticket.state.name())


class RegressionTest(unittest.TestCase):
    """Regression tests for defects found during the review (invalid card, owner check, price update)."""

    def setUp(self) -> None:
        """Create a database with one future event of three seats."""
        self.now = datetime.now(timezone.utc)
        self.db = TicketDB()
        self.db.create_event(Event(EventId(1), "Future Concert", self.now + timedelta(days=3), 3, Decimal("25.00")))
        self.customer = Customer(UserId(1), "Alice Buyer", "alice@example.com")
        self.other = Customer(UserId(2), "Bob Buyer", "bob@example.com")
        self.clerk = Clerk(UserId(10), "Admin Clerk", "clerk@example.com", "EMP-1")

    def _ticket(self, seat: str) -> Ticket:
        return self.db.find_tickets_by_seats(EventId(1), [SeatId(seat)])[0]

    def test_rf8_invalid_card_releases_reserved_seats(self) -> None:
        """RF8: a payment error must not leave seats locked."""
        controller = TicketSeller(self.db, self.db, CreditCardCharges(success_rate=1.0), StandardPricing())
        bad_card = PaymentData("Alice Buyer", "not-a-card", 12, 2099, "123")

        with self.assertRaises(ValueError):
            controller.purchase_access_title(EventId(1), [SeatId("S001")], self.customer, bad_card)

        self.assertEqual("available", self._ticket("S001").state.name())

    def test_locked_ticket_cannot_be_sold_to_another_customer(self) -> None:
        """State guard: only the customer holding the lock can confirm the sale."""
        ticket = Ticket(VoucherId(1), EventId(1), Decimal("10.00"), SeatId("A1"))
        ticket.reserve(self.customer)

        with self.assertRaises(ValueError):
            ticket.confirm_sale(self.other)

    def test_rf11_price_update_applies_to_unsold_tickets(self) -> None:
        """RF11: changing the base price updates unsold seats."""
        controller = TicketSeller(self.db, self.db, FixedPaymentService(True), StandardPricing())
        controller.update_event(self.clerk, Event(EventId(1), "Future Concert", self.now + timedelta(days=3), 3, Decimal("30.00")))

        self.assertEqual({Decimal("30.00")}, {t.base_price for t in self.db.find_tickets_by_event(EventId(1))})


if __name__ == "__main__":
    unittest.main()
