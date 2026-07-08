from __future__ import annotations

from decimal import Decimal
import zlib

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ticketseller.controllers.ticket_seller import TicketSeller
from ticketseller.external_services.credit_card_charges import PaymentData
from ticketseller.models.event import EventId
from ticketseller.models.ticket import SeatId
from ticketseller.models.users import Customer, UserId


class KioskInterface(QWidget):
    """PyQt6 customer interface for browsing events and buying tickets."""

    def __init__(self, controller: TicketSeller) -> None:
        """Initialize the kiosk interface."""
        super().__init__()
        self.controller = controller
        self.setWindowTitle("TicketSeller Kiosk")
        self.event_selector = QComboBox()
        self.seat_list = QListWidget()
        self.total_label = QLabel("Total: 0.00")
        self.name_input = QLineEdit("Demo Customer")
        self.email_input = QLineEdit("customer@example.com")
        self.card_input = QLineEdit("4111111111111111")
        self.cvv_input = QLineEdit("123")
        self.exp_month_input = QLineEdit("12")
        self.exp_year_input = QLineEdit("2099")
        self._build_layout()
        self._load_events()

    def _build_layout(self) -> None:
        """Build widgets and signal connections."""
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select event"))
        layout.addWidget(self.event_selector)
        layout.addWidget(QLabel("Select one or more available seats"))
        self.seat_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        layout.addWidget(self.seat_list)
        layout.addWidget(self.total_label)

        payment_group = QGroupBox("Payment")
        form = QFormLayout(payment_group)
        form.addRow("Name", self.name_input)
        form.addRow("Email", self.email_input)
        form.addRow("Card", self.card_input)
        form.addRow("CVV", self.cvv_input)
        form.addRow("Exp. Month", self.exp_month_input)
        form.addRow("Exp. Year", self.exp_year_input)
        layout.addWidget(payment_group)

        buy_button = QPushButton("Buy Selected Seats")
        refresh_button = QPushButton("Refresh")
        button_grid = QGridLayout()
        button_grid.addWidget(refresh_button, 0, 0)
        button_grid.addWidget(buy_button, 0, 1)
        layout.addLayout(button_grid)

        self.event_selector.currentIndexChanged.connect(self._load_seats)
        self.seat_list.itemSelectionChanged.connect(self._update_total)
        buy_button.clicked.connect(self._buy_selected_seats)
        refresh_button.clicked.connect(self._load_events)

    def _load_events(self) -> None:
        """Load future events into the event selector."""
        self.event_selector.clear()
        for event in self.controller.search_future_events():
            self.event_selector.addItem(f"{event.name} ({event.date:%Y-%m-%d %H:%M})", int(event.id))
        self._load_seats()

    def _load_seats(self, *_args: object) -> None:
        """Load seats for the selected event."""
        self.seat_list.clear()
        event_id = self._current_event_id()
        if event_id is None:
            return
        for ticket in self.controller.get_seating_map(event_id):
            item_text = f"{ticket.seat_id} - {ticket.state.name()} - {ticket.base_price}"
            self.seat_list.addItem(item_text)
            item = self.seat_list.item(self.seat_list.count() - 1)
            # Store the seat id separately from display text.
            item.setData(Qt.ItemDataRole.UserRole, str(ticket.seat_id))
            if not ticket.is_available():
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)

    def _update_total(self) -> None:
        """Update total for selected seats."""
        event_id = self._current_event_id()
        if event_id is None:
            return
        try:
            seats = self._selected_seats()
            tickets = self.controller.get_tickets_by_seats(event_id, seats) if seats else []
            total = self.controller.calculate_total(tickets) if tickets else Decimal("0.00")
            self.total_label.setText(f"Total: {total}")
        except ValueError as exc:
            self._show_error(str(exc))

    def _buy_selected_seats(self) -> None:
        """Purchase the selected seats."""
        event_id = self._current_event_id()
        if event_id is None:
            self._show_error("Select an event first.")
            return
        seats = self._selected_seats()
        if not seats:
            self._show_error("Select at least one available seat.")
            return
        try:
            # Use a stable demo identifier derived from email.
            customer = Customer(
                UserId(zlib.crc32(self.email_input.text().encode("utf-8")) % 1_000_000),
                self.name_input.text(),
                self.email_input.text(),
            )
            expiration_month = self._parse_int_field(self.exp_month_input, "Expiration month")
            expiration_year = self._parse_int_field(self.exp_year_input, "Expiration year")
            payment = PaymentData(
                self.name_input.text(),
                self.card_input.text(),
                expiration_month,
                expiration_year,
                self.cvv_input.text(),
            )
            result = self.controller.purchase_access_title(event_id, seats, customer, payment)
            QMessageBox.information(
                self,
                "Payment",
                result.transaction_id if result.approved else result.error_message or "Declined",
            )
            self._load_seats()
        except (ValueError, PermissionError) as exc:
            self._show_error(str(exc))

    def _current_event_id(self) -> EventId | None:
        """Return the selected event identifier."""
        value = self.event_selector.currentData()
        return EventId(value) if value is not None else None

    def _selected_seats(self) -> list[SeatId]:
        """Return selected seat identifiers."""
        return [SeatId(item.data(Qt.ItemDataRole.UserRole)) for item in self.seat_list.selectedItems()]

    def _show_error(self, message: str) -> None:
        """Display a GUI error dialog."""
        QMessageBox.warning(self, "TicketSeller", message)

    def _parse_int_field(self, field: QLineEdit, label: str) -> int:
        """Parse an integer GUI field with a friendly error message."""
        try:
            return int(field.text())
        except ValueError as exc:
            raise ValueError(f"{label} must be a number.") from exc
