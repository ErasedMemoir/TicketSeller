from __future__ import annotations

import unittest
from datetime import datetime, timezone

from ticketseller.utils import as_utc


class UtilsTest(unittest.TestCase):
    """Unit tests for shared utility functions."""

    def test_as_utc_returns_timezone_aware_datetime(self) -> None:
        """Verify naive datetimes are converted to timezone-aware UTC values."""
        value = as_utc(datetime(2099, 1, 1, 12, 0, 0))

        self.assertEqual(timezone.utc, value.tzinfo)


if __name__ == "__main__":
    unittest.main()
