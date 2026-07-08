from __future__ import annotations

from typing import TYPE_CHECKING

from ticketseller.patterns.state.ticket_state import TicketState

if TYPE_CHECKING:
    from ticketseller.models.ticket import Ticket
    from ticketseller.models.users import Customer


class SoldState(TicketState):
    """Sold state where a ticket cannot be purchased again."""

    def reserve(self, ticket: Ticket, customer: Customer | None = None) -> None:
        """Reject locking of a sold ticket."""
        raise ValueError("Ticket has already been sold.")

    def cancel(self, ticket: Ticket) -> None:
        """Reject cancellation of a completed sale."""
        raise ValueError("Sold tickets cannot be cancelled without refund workflow.")

    def confirm_sale(self, ticket: Ticket, customer: Customer) -> None:
        """Reject duplicate sale confirmation."""
        raise ValueError("Ticket sale has already been confirmed.")

    def is_available(self) -> bool:
        """Return False because the ticket is sold."""
        return False

    def name(self) -> str:
        """Return the state name."""
        return "sold"
