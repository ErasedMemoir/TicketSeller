from __future__ import annotations

from dataclasses import dataclass
import re
from typing import NewType


UserId = NewType("UserId", int)


@dataclass
class User:
    """Base user of the TicketSeller system."""

    id: UserId
    name: str
    email: str

    def __post_init__(self) -> None:
        """Validate common user attributes."""
        if not self.name.strip():
            raise ValueError("User name cannot be empty.")
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", self.email):
            raise ValueError("User email must be valid.")


@dataclass
class Customer(User):
    """Customer who browses events and purchases tickets."""


@dataclass
class Clerk(User):
    """Authorized clerk who manages events."""

    employee_code: str

    def __post_init__(self) -> None:
        """Validate clerk attributes."""
        super().__post_init__()
        if not self.employee_code.strip():
            raise ValueError("Employee code cannot be empty.")
