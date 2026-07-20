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
    """Minimal contract for a rumble backend.

    ``rumble(intensity, balance)``:
      intensity: overall amplitude [0.0–1.0].
      balance:   strong/weak motor split [0.0–1.0]; 0.5 = equal.

    ``set_kernel_gain(gain)``:
      Forward the user's gain to the kernel-level ``FF_GAIN`` so game
      rumble is also affected.  gain is [0.0–1.0]; backends that cannot
      set a global gain should silently no-op.

    ``set_balance(balance)``:
      Store the strong/weak motor split so future intercepted FF effects
      are adjusted.  Only meaningful for backends that intercept
      per-effect (e.g. ``UinputProxy``).  Plain evdev backends no-op.
    """

    def rumble(self, intensity: float, balance: float = 0.5) -> None: ...

    def stop(self) -> None: ...

    def set_kernel_gain(self, gain: float) -> None: ...

    def set_balance(self, balance: float) -> None: ...
