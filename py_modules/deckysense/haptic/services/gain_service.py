"""Gain service.

Owns the current ``HapticParams`` and exposes the operations the
frontend needs: read/write gain, and a preview pulse so the user can
feel the effect of their settings.

Gain is the simplest transform: multiply the requested intensity by
the configured gain, clamp to [0.0, 1.0] (the hardware ceiling).
"""

from __future__ import annotations

from typing import Any, Optional

import decky

from ..adapters import HapticBackend
from ..adapters.inputplumber_adapter import InputPlumberAdapter
from ..domain import DEFAULT_GAIN, HapticParams

SETTING_KEY = "haptic.gain"


class GainService:
    """Single-instance service that owns haptic params."""

    def __init__(self, backend: Optional[HapticBackend] = None) -> None:
        # Default to the InputPlumber adapter (the only one we have today).
        # Tests can inject a mock backend.
        self._backend: HapticBackend = backend or InputPlumberAdapter()
        self._params: HapticParams = HapticParams(gain=DEFAULT_GAIN)

    def load_from_settings(self) -> None:
        stored = decky.get_setting(SETTING_KEY, DEFAULT_GAIN)
        try:
            gain = float(stored)
        except (TypeError, ValueError):
            gain = DEFAULT_GAIN
        self._params = HapticParams(gain=gain).clamped()

    def get_params(self) -> dict[str, Any]:
        return {"gain": self._params.gain}

    def set_gain(self, value: float) -> dict[str, Any]:
        self._params = HapticParams(gain=float(value)).clamped()
        decky.set_setting(SETTING_KEY, self._params.gain)
        return self.get_params()

    def preview(self, raw_intensity: float = 0.5) -> dict[str, Any]:
        """Trigger a rumble at ``raw_intensity * gain``, clamped to 1.0."""
        try:
            amplified = min(1.0, float(raw_intensity) * self._params.gain)
            self._backend.rumble(amplified)
            return {"state": "playing", "intensity": amplified, "gain": self._params.gain}
        except Exception as exc:  # noqa: BLE001
            decky.logger.exception("haptic preview failed")
            return {"state": "error", "error": f"{type(exc).__name__}: {exc}"}

    def stop(self) -> dict[str, Any]:
        try:
            self._backend.stop()
            return {"state": "stopped"}
        except Exception as exc:  # noqa: BLE001
            decky.logger.exception("haptic stop failed")
            return {"state": "error", "error": f"{type(exc).__name__}: {exc}"}


# Module-level singleton so RPC handlers in main.py share state.
_instance: Optional[GainService] = None


def get_gain_service() -> GainService:
    global _instance
    if _instance is None:
        _instance = GainService()
    return _instance
