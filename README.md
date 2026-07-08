# TicketSeller

TicketSeller is a Python MVC application for event ticket sales. It includes a DAO layer, a State pattern implementation for ticket lifecycle management, a Strategy pattern implementation for price calculations, a simulated payment gateway, and PyQt6 desktop interfaces for customers and clerks.

See `PROJECT_TECHNICAL_OVERVIEW.md` for a detailed architecture and design explanation.

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

## Windows Setup

Run these commands from the project root directory:

```cmd
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

## Nix Flake Setup

Run these commands from the project root directory:

```bash
nix develop
python -m unittest discover -s tests
python -m ticketseller.app kiosk
```

To launch the clerk interface:

```bash
python -m ticketseller.app clerk
```

Run directly with Nix apps:

```bash
nix run .#kiosk
nix run .#clerk
nix run .#tests
```
