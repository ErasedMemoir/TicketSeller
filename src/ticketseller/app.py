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
from ticketseller.patterns.strategy.standard_pricing import StandardPricing
from ticketseller.views.clerk_interface import ClerkInterface
from ticketseller.views.kiosk_interface import KioskInterface


def build_demo_controller() -> TicketSeller:
    """Build a controller backed by a JSON database with demo events."""
    # Initialize the DAO to persist data to a JSON file.
    database = TicketDB(Path("database.json"))
    now = datetime.now(timezone.utc)
    
    # Seed demo events only if the database is currently empty.
    if not database.search_future_events():
        database.create_event(
            Event(EventId(1), "Jazz Night", now + timedelta(days=7), 20, Decimal("30.00"), "Blue Hall")
        )
        database.create_event(
            Event(EventId(2), "Classical Gala", now + timedelta(days=14), 15, Decimal("45.00"), "Main Theatre")
        )
        
    return TicketSeller(database, database, CreditCardCharges(success_rate=0.85), StandardPricing())

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
