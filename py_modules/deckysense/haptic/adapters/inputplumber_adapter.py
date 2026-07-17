"""InputPlumber D-Bus adapter for the Lenovo Legion Go S.

Speaks to ``org.shadowblip.Output.ForceFeedback`` on the composite
device that InputPlumber creates for the Go S. We shell out to
``gdbus`` instead of pulling in a D-Bus Python dependency — gdbus is
always present on SteamOS and the rumble path is not latency-critical
enough to justify a native binding.

For a future low-latency path (synthetic patterns, real-time envelope
shaping) we would migrate to ``dbus-python`` or ``jeepney``.
"""

from __future__ import annotations

import subprocess

from . import HapticBackend

DBUS_SERVICE = "org.shadowblip.InputPlumber"
DBUS_PATH = "/org/shadowblip/InputPlumber/CompositeDevice0"
DBUS_INTERFACE = "org.shadowblip.Output.ForceFeedback"


class InputPlumberAdapter(HapticBackend):
    """Talks to InputPlumber via the ``gdbus`` CLI."""

    def rumble(self, intensity: float) -> None:
        clamped = max(0.0, min(float(intensity), 1.0))
        subprocess.run(
            [
                "gdbus",
                "call",
                "--system",
                "--dest",
                DBUS_SERVICE,
                "--object-path",
                DBUS_PATH,
                "--method",
                f"{DBUS_INTERFACE}.Rumble",
                str(clamped),
            ],
            check=True,
            capture_output=True,
            timeout=5,
        )

    def stop(self) -> None:
        subprocess.run(
            [
                "gdbus",
                "call",
                "--system",
                "--dest",
                DBUS_SERVICE,
                "--object-path",
                DBUS_PATH,
                "--method",
                f"{DBUS_INTERFACE}.Stop",
            ],
            check=True,
            capture_output=True,
            timeout=5,
        )
