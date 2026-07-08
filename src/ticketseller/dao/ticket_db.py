from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from ticketseller.dao.interfaces import EventDAO, TicketDAO
from ticketseller.models.event import Event, EventId
from ticketseller.models.ticket import SeatId, Ticket
from ticketseller.models.users import Customer, UserId
from ticketseller.models.voucher import VoucherId
from ticketseller.patterns.state.available_state import AvailableState
from ticketseller.patterns.state.locked_state import LockedState
from ticketseller.patterns.state.sold_state import SoldState
from ticketseller.patterns.state.ticket_state import TicketState
from ticketseller.utils import as_utc


class TicketDB(EventDAO, TicketDAO):
    """Concrete DAO using dictionaries with optional JSON persistence."""

    def __init__(self, connection_string: str | None = None) -> None:
        """Initialize database storage and load persisted data when configured."""
        self.connection_string = connection_string
        self._events: dict[int, Event] = {}
        self._tickets: dict[int, Ticket] = {}
        self._path = Path(connection_string) if connection_string else None
        if self._path and self._path.exists():
            self._load()

    def find_future_events(self) -> list[Event]:
        """Return future events sorted chronologically."""
        now = datetime.now(timezone.utc)
        return sorted(
            (event for event in self._events.values() if as_utc(event.date) >= now),
            key=lambda event: as_utc(event.date),
        )

    def find_event_by_id(self, event_id: EventId) -> Event | None:
        """Return an event from the datastore."""
        return self._events.get(int(event_id))

    def create_event(self, event: Event) -> Event:
        """Create an event and auto-generate tickets when needed."""
        if int(event.id) in self._events:
            raise ValueError("Event already exists.")
        self._events[int(event.id)] = event
        # Keep the seating map aligned with event capacity.
        self._ensure_event_tickets(event)
        self._persist()
        return event

    def update_event(self, event: Event) -> Event:
        """Update an existing event and keep the seating map consistent."""
        if int(event.id) not in self._events:
            raise ValueError("Event does not exist.")
        sold_count = sum(1 for ticket in self.find_tickets_by_event(event.id) if ticket.state.name() == "sold")
        if event.capacity < sold_count:
            raise ValueError("Event capacity cannot be lower than sold tickets.")
        self._events[int(event.id)] = event
        self._ensure_event_tickets(event)
        self._persist()
        return event

    def delete_event(self, event_id: EventId) -> None:
        """Delete an event and all related tickets when no ticket is sold."""
        tickets = self.find_tickets_by_event(event_id)
        if any(ticket.state.name() == "sold" for ticket in tickets):
            raise ValueError("Cannot delete an event with sold tickets.")
        self._events.pop(int(event_id), None)
        self._tickets = {
            key: ticket
            for key, ticket in self._tickets.items()
            if int(ticket.event_id) != int(event_id)
        }
        self._persist()

    def find_tickets_by_event(self, event_id: EventId) -> list[Ticket]:
        """Return tickets for the selected event sorted by seat."""
        return sorted(
            (ticket for ticket in self._tickets.values() if int(ticket.event_id) == int(event_id)),
            key=lambda ticket: str(ticket.seat_id),
        )

    def find_ticket_by_id(self, ticket_id: VoucherId) -> Ticket | None:
        """Return a ticket from the datastore."""
        return self._tickets.get(int(ticket_id))

    def find_tickets_by_seats(self, event_id: EventId, seat_ids: list[SeatId]) -> list[Ticket]:
        """Return matching tickets for the selected seats."""
        wanted = {str(seat_id) for seat_id in seat_ids}
        tickets = [ticket for ticket in self.find_tickets_by_event(event_id) if str(ticket.seat_id) in wanted]
        if len(tickets) != len(wanted):
            raise ValueError("One or more selected seats do not exist.")
        return tickets

    def save_ticket(self, ticket: Ticket) -> Ticket:
        """Persist a single ticket."""
        self._tickets[int(ticket.id)] = ticket
        self._persist()
        return ticket

    def save_tickets(self, tickets: list[Ticket]) -> list[Ticket]:
        """Persist multiple tickets."""
        for ticket in tickets:
            self._tickets[int(ticket.id)] = ticket
        self._persist()
        return tickets

    def _ensure_event_tickets(self, event: Event) -> None:
        """Synchronize event seats without overwriting sold tickets."""
        existing = {str(ticket.seat_id): ticket for ticket in self.find_tickets_by_event(event.id)}
        valid_seats = {f"S{index:03d}" for index in range(1, event.capacity + 1)}
        # Preserve sold seats even when capacity is reduced.
        self._tickets = {
            key: ticket
            for key, ticket in self._tickets.items()
            if int(ticket.event_id) != int(event.id)
            or str(ticket.seat_id) in valid_seats
            or ticket.state.name() == "sold"
        }
        for seat_id in sorted(valid_seats - set(existing)):
            ticket_id = self._next_ticket_id()
            self._tickets[ticket_id] = Ticket(
                id=VoucherId(ticket_id),
                event_id=event.id,
                base_price=event.base_price,
                seat_id=SeatId(seat_id),
            )

    def _next_ticket_id(self) -> int:
        """Return the next ticket identifier."""
        return max(self._tickets.keys(), default=0) + 1

    def _persist(self) -> None:
        """Persist current dictionaries to JSON when a path is configured."""
        if not self._path:
            return
        # Store only JSON-safe primitive values.
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "events": [self._event_to_dict(event) for event in self._events.values()],
            "tickets": [self._ticket_to_dict(ticket) for ticket in self._tickets.values()],
        }
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load(self) -> None:
        """Load dictionaries from a JSON file."""
        data = json.loads(self._path.read_text(encoding="utf-8")) if self._path else {}
        self._events = {item["id"]: self._event_from_dict(item) for item in data.get("events", [])}
        self._tickets = {item["id"]: self._ticket_from_dict(item) for item in data.get("tickets", [])}

    def _event_to_dict(self, event: Event) -> dict[str, Any]:
        """Convert an event to JSON-compatible data."""
        return {
            "id": int(event.id),
            "name": event.name,
            "date": event.date.isoformat(),
            "capacity": event.capacity,
            "base_price": str(event.base_price),
            "venue_name": event.venue_name,
            "description": event.description,
            "metadata": event.metadata,
        }

    def _event_from_dict(self, item: dict[str, Any]) -> Event:
        """Convert JSON-compatible data to an event."""
        return Event(
            id=EventId(item["id"]),
            name=item["name"],
            date=datetime.fromisoformat(item["date"]),
            capacity=item["capacity"],
            base_price=Decimal(item["base_price"]),
            venue_name=item.get("venue_name"),
            description=item.get("description"),
            metadata=item.get("metadata", {}),
        )

    def _ticket_to_dict(self, ticket: Ticket) -> dict[str, Any]:
        """Convert a ticket to JSON-compatible data."""
        return {
            "id": int(ticket.id),
            "event_id": int(ticket.event_id),
            "base_price": str(ticket.base_price),
            "seat_id": str(ticket.seat_id),
            "state": ticket.state.name(),
            "locked_at": ticket.locked_at.isoformat() if ticket.locked_at else None,
            "owner": self._owner_to_dict(ticket.owner),
        }

    def _ticket_from_dict(self, item: dict[str, Any]) -> Ticket:
        """Convert JSON-compatible data to a ticket."""
        return Ticket(
            id=VoucherId(item["id"]),
            event_id=EventId(item["event_id"]),
            base_price=Decimal(item["base_price"]),
            seat_id=SeatId(item["seat_id"]),
            state=self._state_from_name(item["state"]),
            locked_at=datetime.fromisoformat(item["locked_at"]) if item.get("locked_at") else None,
            owner=self._owner_from_dict(item.get("owner")),
        )

    def _state_from_name(self, name: str) -> TicketState:
        """Build a ticket state from its persisted name."""
        # Map persisted state names back to behavior objects.
        states: dict[str, TicketState] = {
            "available": AvailableState(),
            "locked": LockedState(),
            "sold": SoldState(),
        }
        if name not in states:
            raise ValueError(f"Unknown ticket state: {name}")
        return states[name]

    def _owner_to_dict(self, owner: Customer | None) -> dict[str, Any] | None:
        """Convert an owner to JSON-compatible data."""
        if owner is None:
            return None
        return {"id": int(owner.id), "name": owner.name, "email": owner.email}

    def _owner_from_dict(self, item: dict[str, Any] | None) -> Customer | None:
        """Convert JSON-compatible data to a customer."""
        if item is None:
            return None
        return Customer(id=UserId(item["id"]), name=item["name"], email=item["email"])
