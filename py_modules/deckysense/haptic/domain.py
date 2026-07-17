"""Haptic domain models.

Pure dataclasses, no I/O. The services layer composes and validates
these; the adapter layer applies them to the hardware.
"""

from __future__ import annotations

from dataclasses import dataclass

# Conservative defaults for the Lenovo Legion Go S, derived from the
# Phase 0 rumble sweep (gradual response across 0.05–1.0, no obvious
# dead-zone or saturation knee).
DEFAULT_GAIN = 1.0
GAIN_MIN = 0.0
GAIN_MAX = 2.0


@dataclass(frozen=True)
class HapticParams:
    """User-tunable haptic parameters.

    For v0.0.3 only ``gain`` is exposed. Future fields: response curve,
    envelope shape, per-motor intensity.
    """

    gain: float = DEFAULT_GAIN

    def clamped(self) -> "HapticParams":
        clamped_gain = max(GAIN_MIN, min(self.gain, GAIN_MAX))
        return HapticParams(gain=clamped_gain)
