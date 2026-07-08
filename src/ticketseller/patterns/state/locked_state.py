from __future__ import annotations

from typing import TYPE_CHECKING

from ticketseller.patterns.state.ticket_state import TicketState

if TYPE_CHECKING:
    from ticketseller.models.ticket import Ticket
    from ticketseller.models.users import Customer


class LockedState(TicketState):
    """Locked state where a ticket is reserved during payment."""

    def reserve(self, ticket: Ticket, customer: Customer | None = None) -> None:
        """Reject reservation of an already locked ticket."""
        raise ValueError("Ticket is already locked.")

    def cancel(self, ticket: Ticket) -> None:
        """Return the ticket to available state."""
        # Import lazily to avoid circular state imports.
        from ticketseller.patterns.state.available_state import AvailableState

        ticket.set_state(AvailableState())
        ticket.locked_at = None
        ticket.owner = None

    def confirm_sale(self, ticket: Ticket, customer: Customer) -> None:
        """Move the ticket to sold state and assign ownership."""
        # Import lazily to avoid circular state imports.
        from ticketseller.patterns.state.sold_state import SoldState

        ticket.set_state(SoldState())
        ticket.locked_at = None
        ticket.owner = customer

    def is_available(self) -> bool:
        """Return False because the ticket is temporarily unavailable."""
        return False

    def name(self) -> str:
        """Return the state name."""
        return "locked"
