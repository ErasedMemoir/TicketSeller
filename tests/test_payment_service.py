from __future__ import annotations

import unittest
from datetime import datetime
from decimal import Decimal

from ticketseller.external_services.credit_card_charges import CreditCardCharges, PaymentData


class PaymentServiceTest(unittest.TestCase):
    """Unit tests for payment validation and processing."""

    def test_expired_card_month_is_rejected(self) -> None:
        """Verify expiration validation checks month and year."""
        now = datetime.now()
        expired_month = 1 if now.month > 1 else 12
        expired_year = now.year if now.month > 1 else now.year - 1
        payment = PaymentData("Alice Buyer", "4111111111111111", expired_month, expired_year, "123")

        with self.assertRaises(ValueError):
            payment.validate()

    def test_zero_amount_payment_is_approved(self) -> None:
        """Verify zero amount transactions are approved."""
        payment = PaymentData("Alice Buyer", "4111111111111111", 12, 2099, "123")
        result = CreditCardCharges(success_rate=0.0).process_payment(payment, Decimal("0.00"))

        self.assertTrue(result.approved)
        self.assertIsNotNone(result.transaction_id)

    def test_invalid_card_number_is_rejected(self) -> None:
        """Verify non-numeric card numbers are rejected."""
        payment = PaymentData("Alice Buyer", "not-a-card", 12, 2099, "123")

        with self.assertRaises(ValueError):
            payment.validate()

    def test_negative_amount_is_rejected(self) -> None:
        """Verify negative payment amounts are rejected."""
        payment = PaymentData("Alice Buyer", "4111111111111111", 12, 2099, "123")

        with self.assertRaises(ValueError):
            CreditCardCharges(success_rate=1.0).process_payment(payment, Decimal("-1.00"))

    def test_invalid_success_rate_is_rejected(self) -> None:
        """Verify payment gateway success rate bounds."""
        with self.assertRaises(ValueError):
            CreditCardCharges(success_rate=1.5)


if __name__ == "__main__":
    unittest.main()
