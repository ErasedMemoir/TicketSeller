from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from threading import RLock
from typing import Protocol

from ticketseller.dao.interfaces import EventDAO, TicketDAO
from ticketseller.external_services.credit_card_charges import PaymentData, PaymentResult
from ticketseller.models.event import Event, EventId
from ticketseller.models.subscription import Subscription
from ticketseller.models.ticket import SeatId, Ticket
from ticketseller.models.users import Clerk, Customer
from ticketseller.patterns.strategy.pricing_strategy import PricingStrategy
from ticketseller.utils import as_utc


class PaymentService(Protocol):
    """Protocol for payment service adapters."""

    def process_payment(self, payment_data: PaymentData, amount: Decimal) -> PaymentResult:
        """Process a payment request."""


class TicketSeller:
    """Main MVC controller coordinating sales, persistence, pricing, and payments."""

    reservation_timeout = timedelta(minutes=15)

    def __init__(
        self,
        event_dao: EventDAO,
        ticket_dao: TicketDAO,
        payment_service: PaymentService,
        pricing_strategy: PricingStrategy,
    ) -> None:
        """Initialize controller dependencies."""
        self.event_dao = event_dao
        self.ticket_dao = ticket_dao
        self.payment_service = payment_service
        self.pricing_strategy = pricing_strategy
        self._reservation_lock = RLock()

    def set_pricing_strategy(self, pricing_strategy: PricingStrategy) -> None:
        """Change the pricing strategy at runtime."""
        self.pricing_strategy = pricing_strategy

    def check_availability(self, event_id: EventId, seat_ids: list[SeatId]) -> bool:
        """Return True when all selected seats exist and are available."""
        # Release stale locks before checking availability.
        self.release_expired_reservations(event_id)
        if len({str(seat_id) for seat_id in seat_ids}) != len(seat_ids):
            return False
        tickets = self.ticket_dao.find_tickets_by_seats(event_id, seat_ids)
        return len(tickets) == len(seat_ids) and all(ticket.is_available() for ticket in tickets)

    def calculate_total(self, tickets: list[Ticket], subscription: Subscription | None = None) -> Decimal:
        """Calculate the order total using the active pricing strategy."""
        return self.pricing_strategy.calculate_total(tickets, subscription)

    def find_event_by_id(self, event_id: EventId) -> Event | None:
        """Return an event by identifier."""
        return self.event_dao.find_event_by_id(event_id)

    def get_tickets_by_seats(self, event_id: EventId, seat_ids: list[SeatId]) -> list[Ticket]:
        """Return tickets for selected seats."""
        return self.ticket_dao.find_tickets_by_seats(event_id, seat_ids)

    def reserve_seats(self, event_id: EventId, seat_ids: list[SeatId], customer: Customer | None = None) -> list[Ticket]:
        """Temporarily lock selected seats during checkout."""
        # Protect the check-and-lock sequence in this process.
        with self._reservation_lock:
            self.release_expired_reservations(event_id)
            if len({str(seat_id) for seat_id in seat_ids}) != len(seat_ids):
                raise ValueError("Duplicate seats cannot be selected.")
            tickets = self.ticket_dao.find_tickets_by_seats(event_id, seat_ids)
            if not tickets:
                raise ValueError("At least one seat must be selected.")
            if any(not ticket.is_available() for ticket in tickets):
                raise ValueError("One or more selected seats are not available.")
            for ticket in tickets:
                ticket.reserve(customer)
            return self.ticket_dao.save_tickets(tickets)

    def purchase_access_title(
        self,
        event_id: EventId,
        seat_ids: list[SeatId],
        customer: Customer,
        payment_data: PaymentData,
        subscription: Subscription | None = None,
    ) -> PaymentResult:
        """Purchase tickets by reserving seats, charging payment, and confirming sale."""
        # Roll back seat locks if the simulated payment fails.
        tickets = self.reserve_seats(event_id, seat_ids, customer)
        total = self.calculate_total(tickets, subscription)
        result = self.payment_service.process_payment(payment_data, total)
        if result.approved:
            self.confirm_sale(tickets, customer)
        else:
            self.cancel_reservation(tickets)
        return result

    def confirm_sale(self, tickets: list[Ticket], customer: Customer) -> list[Ticket]:
        """Confirm selected locked tickets as sold."""
        for ticket in tickets:
            ticket.confirm_sale(customer)
        return self.ticket_dao.save_tickets(tickets)

    def cancel_reservation(self, tickets: list[Ticket]) -> list[Ticket]:
        """Cancel selected locked tickets and restore availability."""
        for ticket in tickets:
            ticket.cancel()
        return self.ticket_dao.save_tickets(tickets)

    def search_future_events(self) -> list[Event]:
        """Return future events available for browsing."""
        return self.event_dao.find_future_events()

    def get_seating_map(self, event_id: EventId) -> list[Ticket]:
        """Return the seating map represented as event tickets."""
        self.release_expired_reservations(event_id)
        return self.ticket_dao.find_tickets_by_event(event_id)

    def release_expired_reservations(self, event_id: EventId | None = None) -> list[Ticket]:
        """Release locked tickets whose reservation timeout has expired."""
        # Prevent abandoned checkouts from holding seats forever.
        now = datetime.now(timezone.utc)
        tickets = self._tickets_for_timeout_check(event_id)
        expired = []
        for ticket in tickets:
            if ticket.state.name() == "locked" and ticket.locked_at is not None:
                locked_at = as_utc(ticket.locked_at)
                if now - locked_at >= self.reservation_timeout:
                    ticket.cancel()
                    expired.append(ticket)
        if expired:
            self.ticket_dao.save_tickets(expired)
        return expired

    def create_event(self, clerk: Clerk, event: Event) -> Event:
        """Create an event after clerk authorization validation."""
        self._verify_clerk(clerk)
        self._verify_future_event(event)
        return self.event_dao.create_event(event)

    def update_event(self, clerk: Clerk, event: Event) -> Event:
        """Update an event after clerk authorization validation."""
        self._verify_clerk(clerk)
        self._verify_future_event(event)
        return self.event_dao.update_event(event)

    def delete_event(self, clerk: Clerk, event_id: EventId) -> None:
        """Delete an event after clerk authorization validation."""
        self._verify_clerk(clerk)
        self.event_dao.delete_event(event_id)

    def _verify_clerk(self, clerk: Clerk) -> None:
        """Validate clerk authorization for administrative actions."""
        if not isinstance(clerk, Clerk) or not clerk.employee_code.strip():
            raise PermissionError("A valid clerk is required.")

    def _verify_future_event(self, event: Event) -> None:
        """Validate that an event is scheduled in the future."""
        if as_utc(event.date) < datetime.now(timezone.utc):
            raise ValueError("Event date must be in the future.")

    def _tickets_for_timeout_check(self, event_id: EventId | None) -> list[Ticket]:
        """Return tickets that should be inspected for reservation expiry."""
        if event_id is None:
            events = self.event_dao.find_future_events()
            tickets: list[Ticket] = []
            for event in events:
                tickets.extend(self.ticket_dao.find_tickets_by_event(event.id))
            return tickets
        return self.ticket_dao.find_tickets_by_event(event_id)
