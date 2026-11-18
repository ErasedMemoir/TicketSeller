from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from PyQt6.QtWidgets import QApplication

from pathlib import Path

from ticketseller.controllers.ticket_seller import TicketSeller
from ticketseller.dao.ticket_db import TicketDB
from ticketseller.external_services.credit_card_charges import CreditCardCharges
from ticketseller.models.event import Event, EventId
from ticketseller.models.subscription import Subscription
from ticketseller.models.voucher import VoucherId
from ticketseller.patterns.strategy.standard_pricing import StandardPricing
from ticketseller.patterns.strategy.subscription_pricing import SubscriptionPricing
from ticketseller.views.clerk_interface import ClerkInterface
from ticketseller.views.kiosk_interface import KioskInterface


def build_demo_controller() -> TicketSeller:
    """Build a controller backed by a JSON database with demo events."""
    # Initialize the DAO to persist data to a JSON file.
    database = TicketDB(Path("database.json"))
    now = datetime.now(timezone.utc)
    
    # Seed demo data only if it is not already in the database.
    if database.find_event_by_id(EventId(1)) is None:
        database.create_event(
            Event(EventId(1), "Jazz Night", now + timedelta(days=7), 20, Decimal("30.00"), "Blue Hall")
        )
    if database.find_event_by_id(EventId(2)) is None:
        database.create_event(
            Event(EventId(2), "Classical Gala", now + timedelta(days=14), 15, Decimal("45.00"), "Main Theatre")
        )
    if database.find_subscription_by_id(VoucherId(100)) is None:
        # Demo subscription: code 100, 50% discount on both demo events.
        database.create_subscription(
            Subscription(VoucherId(100), EventId(1), Decimal("60.00"), [EventId(1), EventId(2)], "Season Pass", Decimal("0.50"))
        )

    return TicketSeller(
        database,
        database,
        CreditCardCharges(success_rate=0.85),
        StandardPricing(),
        subscription_strategy=SubscriptionPricing(),
        subscription_dao=database,
    )

def main() -> int:
    """Launch the requested PyQt6 interface."""
    app = QApplication(sys.argv)
    controller = build_demo_controller()
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "kiosk"
    # Select the requested desktop interface.
    window = ClerkInterface(controller) if mode == "clerk" else KioskInterface(controller)
    window.resize(720, 560)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
