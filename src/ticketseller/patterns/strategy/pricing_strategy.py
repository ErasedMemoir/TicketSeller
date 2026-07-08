from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ticketseller.models.subscription import Subscription
    from ticketseller.models.ticket import Ticket


class PricingStrategy(ABC):
    """Abstract Strategy Pattern interface for price calculations."""

    @abstractmethod
    def calculate_total(self, tickets: list[Ticket], subscription: Subscription | None = None) -> Decimal:
        """Calculate the total order amount."""


def quantize_money(amount: Decimal) -> Decimal:
    """Round a monetary amount to two decimal places."""
    return amount.quantize(Decimal("0.01"))
