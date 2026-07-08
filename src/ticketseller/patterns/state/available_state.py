from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from ticketseller.patterns.state.ticket_state import TicketState

if TYPE_CHECKING:
    from ticketseller.models.ticket import Ticket
    from ticketseller.models.users import Customer


class AvailableState(TicketState):
    """Available state where a ticket can be temporarily locked."""

    def reserve(self, ticket: Ticket, customer: Customer | None = None) -> None:
        """Move the ticket to locked state and record reservation data."""
        # Import lazily to avoid circular state imports.
        from ticketseller.patterns.state.locked_state import LockedState

        ticket.set_state(LockedState())
        ticket.locked_at = datetime.now(timezone.utc)
        ticket.owner = customer

    def cancel(self, ticket: Ticket) -> None:
        """Leave an already available ticket unchanged."""
        ticket.locked_at = None
        ticket.owner = None

    def confirm_sale(self, ticket: Ticket, customer: Customer) -> None:
        """Reject direct sale confirmation without a temporary lock."""
        raise ValueError("Ticket must be locked before sale confirmation.")

    def is_available(self) -> bool:
        """Return True because the ticket is available."""
        return True

    def name(self) -> str:
        """Return the state name."""
        return "available"
