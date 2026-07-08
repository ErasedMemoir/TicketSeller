from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from ticketseller.dao.ticket_db import TicketDB
from ticketseller.models.event import Event, EventId
from ticketseller.models.ticket import SeatId
from ticketseller.models.users import Customer, UserId


class TicketDBTest(unittest.TestCase):
    """Unit tests for DAO persistence and seat synchronization."""

    def test_json_persistence_roundtrip(self) -> None:
        """Verify events and tickets are restored from JSON storage."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ticketseller.json"
            database = TicketDB(str(path))
            event = Event(EventId(1), "Stored Event", datetime.now(timezone.utc) + timedelta(days=1), 2, Decimal("10.00"))
            database.create_event(event)

            restored = TicketDB(str(path))

            self.assertEqual("Stored Event", restored.find_event_by_id(EventId(1)).name)
            self.assertEqual(2, len(restored.find_tickets_by_event(EventId(1))))

    def test_create_event_generates_tickets(self) -> None:
        """Verify event creation generates a complete seating map."""
        database = TicketDB()
        event = Event(EventId(1), "Created Event", datetime.now(timezone.utc) + timedelta(days=1), 3, Decimal("10.00"))

        created = database.create_event(event)
        seats = [str(ticket.seat_id) for ticket in database.find_tickets_by_event(EventId(1))]

        self.assertEqual(event, created)
        self.assertEqual(["S001", "S002", "S003"], seats)

    def test_create_duplicate_event_is_rejected(self) -> None:
        """Verify duplicate event identifiers are rejected."""
        database = TicketDB()
        event = Event(EventId(1), "Duplicate Event", datetime.now(timezone.utc) + timedelta(days=1), 1, Decimal("10.00"))
        database.create_event(event)

        with self.assertRaises(ValueError):
            database.create_event(event)

    def test_update_missing_event_is_rejected(self) -> None:
        """Verify updating an unknown event fails."""
        database = TicketDB()
        event = Event(EventId(1), "Missing Event", datetime.now(timezone.utc) + timedelta(days=1), 1, Decimal("10.00"))

        with self.assertRaises(ValueError):
            database.update_event(event)

    def test_delete_event_removes_event_and_tickets(self) -> None:
        """Verify deleting an unsold event removes its seating map."""
        database = TicketDB()
        event = Event(EventId(1), "Deleted Event", datetime.now(timezone.utc) + timedelta(days=1), 2, Decimal("10.00"))
        database.create_event(event)

        database.delete_event(EventId(1))

        self.assertIsNone(database.find_event_by_id(EventId(1)))
        self.assertEqual([], database.find_tickets_by_event(EventId(1)))

    def test_save_ticket_updates_ticket_state(self) -> None:
        """Verify saving a ticket persists its current state."""
        database = TicketDB()
        customer = Customer(UserId(1), "Alice Buyer", "alice@example.com")
        event = Event(EventId(1), "Ticket Event", datetime.now(timezone.utc) + timedelta(days=1), 1, Decimal("10.00"))
        database.create_event(event)
        ticket = database.find_tickets_by_event(EventId(1))[0]
        ticket.reserve(customer)

        database.save_ticket(ticket)

        self.assertEqual("locked", database.find_ticket_by_id(ticket.id).state.name())

    def test_save_tickets_updates_multiple_tickets(self) -> None:
        """Verify saving multiple tickets persists all states."""
        database = TicketDB()
        customer = Customer(UserId(1), "Alice Buyer", "alice@example.com")
        event = Event(EventId(1), "Multi Ticket Event", datetime.now(timezone.utc) + timedelta(days=1), 2, Decimal("10.00"))
        database.create_event(event)
        tickets = database.find_tickets_by_event(EventId(1))
        for ticket in tickets:
            ticket.reserve(customer)

        database.save_tickets(tickets)

        self.assertEqual(["locked", "locked"], [ticket.state.name() for ticket in database.find_tickets_by_event(EventId(1))])

    def test_capacity_update_adds_and_removes_expected_seats(self) -> None:
        """Verify capacity changes keep valid seat labels only."""
        database = TicketDB()
        event = Event(EventId(1), "Resizable Event", datetime.now(timezone.utc) + timedelta(days=1), 4, Decimal("15.00"))
        database.create_event(event)

        database.update_event(Event(EventId(1), "Resizable Event", event.date, 2, Decimal("15.00")))
        seats_after_shrink = [str(ticket.seat_id) for ticket in database.find_tickets_by_event(EventId(1))]
        self.assertEqual(["S001", "S002"], seats_after_shrink)

        database.update_event(Event(EventId(1), "Resizable Event", event.date, 5, Decimal("15.00")))
        seats_after_growth = [str(ticket.seat_id) for ticket in database.find_tickets_by_event(EventId(1))]
        self.assertEqual(["S001", "S002", "S003", "S004", "S005"], seats_after_growth)

    def test_find_tickets_by_missing_seat_raises_error(self) -> None:
        """Verify unknown seats are rejected."""
        database = TicketDB()
        event = Event(EventId(1), "Small Event", datetime.now(timezone.utc) + timedelta(days=1), 1, Decimal("15.00"))
        database.create_event(event)

        with self.assertRaises(ValueError):
            database.find_tickets_by_seats(EventId(1), [SeatId("S999")])

    def test_unknown_persisted_state_raises_descriptive_error(self) -> None:
        """Verify corrupt ticket state names are rejected clearly."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ticketseller.json"
            path.write_text(
                json.dumps(
                    {
                        "events": [],
                        "tickets": [
                            {
                                "id": 1,
                                "event_id": 1,
                                "base_price": "10.00",
                                "seat_id": "S001",
                                "state": "broken",
                                "locked_at": None,
                                "owner": None,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                TicketDB(str(path))

    def test_find_future_events_filters_and_sorts_dates(self) -> None:
        """Verify future events are filtered and sorted."""
        database = TicketDB()
        now = datetime.now(timezone.utc)
        database.create_event(Event(EventId(1), "Later", now + timedelta(days=2), 1, Decimal("10.00")))
        database.create_event(Event(EventId(2), "Sooner", now + timedelta(days=1), 1, Decimal("10.00")))
        database.create_event(Event(EventId(3), "Past", now - timedelta(days=1), 1, Decimal("10.00")))

        events = database.find_future_events()

        self.assertEqual(["Sooner", "Later"], [event.name for event in events])

    def test_find_ticket_by_id_returns_ticket(self) -> None:
        """Verify a ticket can be retrieved by identifier."""
        database = TicketDB()
        event = Event(EventId(1), "Lookup Event", datetime.now(timezone.utc) + timedelta(days=1), 1, Decimal("10.00"))
        database.create_event(event)
        ticket = database.find_tickets_by_event(EventId(1))[0]

        found = database.find_ticket_by_id(ticket.id)

        self.assertEqual(ticket, found)

    def test_delete_event_with_sold_ticket_is_rejected(self) -> None:
        """Verify events with sold tickets cannot be deleted."""
        database = TicketDB()
        customer = Customer(UserId(1), "Alice Buyer", "alice@example.com")
        event = Event(EventId(1), "Sold Event", datetime.now(timezone.utc) + timedelta(days=1), 1, Decimal("10.00"))
        database.create_event(event)
        ticket = database.find_tickets_by_event(EventId(1))[0]
        ticket.reserve(customer)
        ticket.confirm_sale(customer)
        database.save_ticket(ticket)

        with self.assertRaises(ValueError):
            database.delete_event(EventId(1))

    def test_capacity_shrink_preserves_sold_ticket_outside_new_capacity(self) -> None:
        """Verify sold seats are not removed during capacity shrink."""
        database = TicketDB()
        customer = Customer(UserId(1), "Alice Buyer", "alice@example.com")
        event = Event(EventId(1), "Protected Event", datetime.now(timezone.utc) + timedelta(days=1), 3, Decimal("10.00"))
        database.create_event(event)
        ticket = database.find_tickets_by_seats(EventId(1), [SeatId("S003")])[0]
        ticket.reserve(customer)
        ticket.confirm_sale(customer)
        database.save_ticket(ticket)

        database.update_event(Event(EventId(1), "Protected Event", event.date, 1, Decimal("10.00")))
        seats = [str(ticket.seat_id) for ticket in database.find_tickets_by_event(EventId(1))]

        self.assertEqual(["S001", "S003"], seats)


if __name__ == "__main__":
    unittest.main()
