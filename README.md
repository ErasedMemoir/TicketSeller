# TicketSeller

TicketSeller is a Python MVC application for event ticket sales. It includes a DAO layer, a State pattern implementation for ticket lifecycle management, a Strategy pattern implementation for price calculations, a simulated payment gateway, and PyQt6 desktop interfaces for customers and clerks.

Project for the Software Engineering course (Ingegneria del Software), Università Politecnica delle Marche, A.Y. 2025/2026.

## Documentation

- [`docs/TicketSeller_documentazione.pdf`](docs/TicketSeller_documentazione.pdf): project documentation (Italian)
- [`docs/ticket_seller_EA.qea`](docs/ticket_seller_EA.qea): UML model (Enterprise Architect)
- [`docs/latex/`](docs/latex/): LaTeX sources of the documentation

## Project Structure

```text
src/ticketseller/
  app.py               entry point, builds the objects and opens the GUI
  views/               PyQt6 interfaces (kiosk and clerk)
  controllers/         TicketSeller controller
  models/              Event, Voucher, Ticket, Subscription, users
  dao/                 DAO interfaces and TicketDB (JSON file)
  patterns/state/      ticket states (Available, Locked, Sold)
  patterns/strategy/   pricing strategies (Standard, Group, Subscription)
  external_services/   simulated credit card payment
tests/                 unittest test suite
```

## Run Tests

```cmd
python -m unittest discover -s tests
```

## Launch GUI

```cmd
python -m ticketseller.app kiosk
python -m ticketseller.app clerk
```

After editable installation, the console script is also available:

```cmd
ticketseller kiosk
ticketseller clerk
```

## Linux / NixOS Setup

```sh
nix develop      # or: nix-shell
python -m unittest discover -s tests -v
python -m ticketseller.app kiosk
```

The demo database contains the subscription code `100` (50% discount on the demo events).

## Windows Setup

Run these commands from the project root directory:

```cmd
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```
