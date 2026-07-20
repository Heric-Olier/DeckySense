"""Haptic hardware adapters.

Every backend implements the ``HapticBackend`` Protocol so the service
layer can hot-swap between them at runtime without knowing the hardware
details.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class HapticBackend(Protocol):
    """Contract for a rumble backend.

    Each backend declares its identity and capabilities so the frontend
    can render the right controls for the active mode.

    Feature flags
    -------------
    ``gain``       — frontend gain slider is supported.
    ``balance``    — per-effect strong/weak motor split is supported.
    ``game_gain``  — gain setting propagates to games, not just preview.
    ``game_balance`` — balance setting propagates to games, not just preview.
    """

    # ── identity ----------------------------------------------------------
    @property
    def id(self) -> str: ...
    @property
    def name(self) -> str: ...
    @property
    def description(self) -> str: ...
    @property
    def features(self) -> frozenset[str]: ...

    # ── actions -----------------------------------------------------------
    def rumble(self, intensity: float, balance: float = 0.5) -> None: ...
    def stop(self) -> None: ...
    def set_kernel_gain(self, gain: float) -> None: ...
    def set_balance(self, balance: float) -> None: ...
    def close(self) -> None: ...
