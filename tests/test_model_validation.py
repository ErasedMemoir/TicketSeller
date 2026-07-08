from __future__ import annotations

import unittest
from datetime import datetime, timezone
from decimal import Decimal

from ticketseller.models.event import Event, EventId
from ticketseller.models.subscription import Subscription
from ticketseller.models.users import Customer, UserId
from ticketseller.models.voucher import VoucherId


class ModelValidationTest(unittest.TestCase):
    """Unit tests for model validation rules."""

    def test_event_rejects_invalid_capacity(self) -> None:
        """Verify events require positive capacity."""
        with self.assertRaises(ValueError):
            Event(EventId(1), "Invalid", datetime.now(timezone.utc), 0, Decimal("10.00"))

    def test_customer_rejects_invalid_email(self) -> None:
        """Verify users require a valid email shape."""
        with self.assertRaises(ValueError):
            Customer(UserId(1), "Alice", "invalid-email")

        with self.assertRaises(ValueError):
            Customer(UserId(1), "Alice", "@")

    def test_subscription_rejects_invalid_discount(self) -> None:
        """Verify subscription discount rate bounds."""
        with self.assertRaises(ValueError):
            Subscription(VoucherId(1), EventId(1), Decimal("10.00"), discount_rate=Decimal("1.50"))


if __name__ == "__main__":
    unittest.main()
