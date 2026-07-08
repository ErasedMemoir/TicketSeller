from __future__ import annotations

from decimal import Decimal, InvalidOperation

from PyQt6.QtCore import QDate, QDateTime, QTime
from PyQt6.QtWidgets import QDateTimeEdit, QFormLayout, QLabel, QLineEdit, QListWidget, QMessageBox, QPushButton, QSpinBox, QVBoxLayout, QWidget

from ticketseller.controllers.ticket_seller import TicketSeller
from ticketseller.models.event import Event, EventId
from ticketseller.models.users import Clerk, UserId


class ClerkInterface(QWidget):
    """PyQt6 clerk interface for creating, editing, and deleting events."""

    def __init__(self, controller: TicketSeller) -> None:
        """Initialize the clerk administration interface."""
        super().__init__()
        self.controller = controller
        self.clerk = Clerk(UserId(100), "Admin Clerk", "clerk@example.com", "EMP-001")
        self.setWindowTitle("TicketSeller Clerk")
        self.event_list = QListWidget()
        self.id_input = QSpinBox()
        self.id_input.setMaximum(999999)
        self.name_input = QLineEdit()
        self.date_input = QDateTimeEdit()
        self.date_input.setCalendarPopup(True)
        self.capacity_input = QSpinBox()
        self.capacity_input.setMinimum(1)
        self.capacity_input.setMaximum(100000)
        self.price_input = QLineEdit("25.00")
        self.venue_input = QLineEdit()
        self._build_layout()
        self._refresh_events()

    def _build_layout(self) -> None:
        """Build administration widgets and connect actions."""
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Events"))
        layout.addWidget(self.event_list)

        form = QFormLayout()
        form.addRow("ID", self.id_input)
        form.addRow("Name", self.name_input)
        form.addRow("Date", self.date_input)
        form.addRow("Capacity", self.capacity_input)
        form.addRow("Base Price", self.price_input)
        form.addRow("Venue", self.venue_input)
        layout.addLayout(form)

        create_button = QPushButton("Create")
        update_button = QPushButton("Update")
        delete_button = QPushButton("Delete")
        refresh_button = QPushButton("Refresh")
        layout.addWidget(create_button)
        layout.addWidget(update_button)
        layout.addWidget(delete_button)
        layout.addWidget(refresh_button)

        create_button.clicked.connect(self._create_event)
        update_button.clicked.connect(self._update_event)
        delete_button.clicked.connect(self._delete_event)
        refresh_button.clicked.connect(self._refresh_events)
        self.event_list.currentItemChanged.connect(self._load_selected_event)

    def _refresh_events(self) -> None:
        """Refresh the event list from the controller."""
        self.event_list.clear()
        for event in self.controller.search_future_events():
            self.event_list.addItem(f"{int(event.id)} - {event.name} - {event.date:%Y-%m-%d %H:%M}")

    def _build_event(self) -> Event:
        """Build an event object from form values."""
        # Convert GUI field values into a domain object.
        return Event(
            id=EventId(self.id_input.value()),
            name=self.name_input.text(),
            date=self.date_input.dateTime().toPyDateTime(),
            capacity=self.capacity_input.value(),
            base_price=self._parse_price(),
            venue_name=self.venue_input.text() or None,
        )

    def _create_event(self) -> None:
        """Create an event through the controller."""
        try:
            self.controller.create_event(self.clerk, self._build_event())
            self._refresh_events()
        except (InvalidOperation, ValueError, PermissionError) as exc:
            self._show_error(str(exc))

    def _update_event(self) -> None:
        """Update an event through the controller."""
        try:
            self.controller.update_event(self.clerk, self._build_event())
            self._refresh_events()
        except (InvalidOperation, ValueError, PermissionError) as exc:
            self._show_error(str(exc))

    def _delete_event(self) -> None:
        """Delete an event through the controller."""
        try:
            self.controller.delete_event(self.clerk, EventId(self.id_input.value()))
            self._refresh_events()
        except (ValueError, PermissionError) as exc:
            self._show_error(str(exc))

    def _load_selected_event(self, *_args: object) -> None:
        """Load selected event identifier into the form."""
        item = self.event_list.currentItem()
        if item is None:
            return
        event_id = int(item.text().split(" - ", 1)[0])
        event = self.controller.find_event_by_id(EventId(event_id))
        if event is None:
            return
        self.id_input.setValue(int(event.id))
        self.name_input.setText(event.name)
        self.date_input.setDateTime(
            QDateTime(
                QDate(event.date.year, event.date.month, event.date.day),
                QTime(event.date.hour, event.date.minute, event.date.second),
            )
        )
        self.capacity_input.setValue(event.capacity)
        self.price_input.setText(str(event.base_price))
        self.venue_input.setText(event.venue_name or "")

    def _show_error(self, message: str) -> None:
        """Display a GUI error dialog."""
        QMessageBox.warning(self, "TicketSeller", message)

    def _parse_price(self) -> Decimal:
        """Parse and validate the price field."""
        try:
            # Normalize clerk-entered prices to currency precision.
            return Decimal(self.price_input.text()).quantize(Decimal("0.01"))
        except InvalidOperation as exc:
            raise ValueError("Base price must be a valid number.") from exc
