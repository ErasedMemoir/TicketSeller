from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, NewType

from ticketseller.models.event import EventId
from ticketseller.models.voucher import Voucher, VoucherId
from ticketseller.patterns.state.available_state import AvailableState
from ticketseller.patterns.state.ticket_state import TicketState

if TYPE_CHECKING:
    from ticketseller.models.users import Customer


SeatId = NewType("SeatId", str)


@dataclass
class Ticket(Voucher):
    """Single ticket associated with an event and a seat."""

    seat_id: SeatId
    state: TicketState = field(default_factory=AvailableState)
    locked_at: datetime | None = None
    owner: Customer | None = None

    def __init__(
        self,
        id: VoucherId,
        event_id: EventId,
        base_price: Decimal,
        seat_id: SeatId,
        state: TicketState | None = None,
        locked_at: datetime | None = None,
        owner: Customer | None = None,
    ) -> None:
        """Initialize a ticket with an optional lifecycle state."""
        super().__init__(id=id, event_id=event_id, base_price=base_price)
        self.seat_id = seat_id
        self.state = state or AvailableState()
        self.locked_at = locked_at
        self.owner = owner

    def set_state(self, state: TicketState) -> None:
        """Change the current ticket state."""
        self.state = state

    def reserve(self, customer: Customer | None = None) -> None:
        """Temporarily lock the ticket during checkout."""
        self.state.reserve(self, customer)

    def cancel(self) -> None:
        """Cancel the current reservation according to the ticket state."""
        self.state.cancel(self)

    def confirm_sale(self, customer: Customer) -> None:
        """Confirm the ticket sale after approved payment."""
        self.state.confirm_sale(self, customer)

    def is_available(self) -> bool:
        """Return True when the ticket can be selected for purchase."""
        return self.state.is_available()
