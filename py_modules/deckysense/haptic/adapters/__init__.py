"""Haptic hardware adapters.

The ``HapticBackend`` Protocol is the port; concrete implementations
are devices (``InputPlumberAdapter`` for the Legion Go S today, future
``SysfsAdapter`` / ``HidrawAdapter`` if other devices need them).

Going through a Protocol keeps the service layer hardware-agnostic
and lets us mock the backend in tests.
"""

from __future__ import annotations

from typing import Protocol


class HapticBackend(Protocol):
    """Minimal contract for a rumble backend."""

    def rumble(self, intensity: float) -> None: ...

    def stop(self) -> None: ...
