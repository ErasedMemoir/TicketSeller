from __future__ import annotations

import random
import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class PaymentData:
    """Payment data entered by a customer."""

    card_holder: str
    card_number: str
    expiration_month: int
    expiration_year: int
    cvv: str

    def validate(self) -> None:
        """Validate basic card data without storing sensitive details."""
        if not self.card_holder.strip():
            raise ValueError("Card holder cannot be empty.")
        if not self.card_number.isdigit() or len(self.card_number) < 12:
            raise ValueError("Card number must contain at least 12 digits.")
        if not 1 <= self.expiration_month <= 12:
            raise ValueError("Expiration month must be between 1 and 12.")
        now = datetime.now()
        if self.expiration_year < now.year or (
            self.expiration_year == now.year and self.expiration_month < now.month
        ):
            raise ValueError("Payment card has expired.")
        if not self.cvv.isdigit() or len(self.cvv) not in {3, 4}:
            raise ValueError("CVV must contain 3 or 4 digits.")


@dataclass(frozen=True)
class PaymentResult:
    """Result returned by payment processing."""

    approved: bool
    transaction_id: str | None = None
    error_message: str | None = None


class CreditCardCharges:
    """Simulated adapter toward an external credit card agency."""

    def __init__(self, agency_endpoint: str | None = None, success_rate: float = 0.85) -> None:
        """Initialize payment service simulation settings."""
        if not 0.0 <= success_rate <= 1.0:
            raise ValueError("Success rate must be between 0 and 1.")
        self.agency_endpoint = agency_endpoint
        self.success_rate = success_rate

    def process_payment(self, payment_data: PaymentData, amount: Decimal) -> PaymentResult:
        """Process a simulated payment request through the external gateway."""
        # Validate locally before simulating the gateway response.
        payment_data.validate()
        if amount < Decimal("0.00"):
            raise ValueError("Payment amount cannot be negative.")
        if amount == Decimal("0.00"):
            return PaymentResult(approved=True, transaction_id=f"FREE-{uuid.uuid4().hex[:12]}")
        if random.random() <= self.success_rate:
            return PaymentResult(approved=True, transaction_id=f"TX-{uuid.uuid4().hex[:12]}")
        return PaymentResult(approved=False, error_message="Payment declined by simulated gateway.")
