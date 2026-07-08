from __future__ import annotations

from abc import ABC, abstractmethod

from ticketseller.models.event import Event, EventId
from ticketseller.models.ticket import SeatId, Ticket
from ticketseller.models.voucher import VoucherId


class EventDAO(ABC):
    """DAO interface for event persistence."""

    @abstractmethod
    def find_future_events(self) -> list[Event]:
        """Return future events sorted by date."""

    @abstractmethod
    def find_event_by_id(self, event_id: EventId) -> Event | None:
        """Return an event by identifier, if present."""

    @abstractmethod
    def create_event(self, event: Event) -> Event:
        """Create an event in the datastore."""

    @abstractmethod
    def update_event(self, event: Event) -> Event:
        """Update an existing event in the datastore."""

    @abstractmethod
    def delete_event(self, event_id: EventId) -> None:
        """Delete an event from the datastore."""


class TicketDAO(ABC):
    """DAO interface for ticket persistence."""

    @abstractmethod
    def find_tickets_by_event(self, event_id: EventId) -> list[Ticket]:
        """Return all tickets for an event."""

    @abstractmethod
    def find_ticket_by_id(self, ticket_id: VoucherId) -> Ticket | None:
        """Return a ticket by identifier, if present."""

    @abstractmethod
    def find_tickets_by_seats(self, event_id: EventId, seat_ids: list[SeatId]) -> list[Ticket]:
        """Return tickets matching selected seats for an event."""

    @abstractmethod
    def save_ticket(self, ticket: Ticket) -> Ticket:
        """Persist one ticket."""

    @abstractmethod
    def save_tickets(self, tickets: list[Ticket]) -> list[Ticket]:
        """Persist multiple tickets."""
