from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ticketseller.models.ticket import Ticket
    from ticketseller.models.users import Customer


class TicketState(ABC):
    """Abstract State Pattern interface for ticket lifecycle rules."""

    @abstractmethod
    def reserve(self, ticket: Ticket, customer: Customer | None = None) -> None:
        """Attempt to temporarily lock the ticket."""

    @abstractmethod
    def cancel(self, ticket: Ticket) -> None:
        """Attempt to cancel the reservation or restore availability."""

    @abstractmethod
    def confirm_sale(self, ticket: Ticket, customer: Customer) -> None:
        """Attempt to confirm the sale of the ticket."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return whether this state represents an available ticket."""

    @abstractmethod
    def name(self) -> str:
        """Return the readable state name."""
