"""InputPlumber D-Bus adapter for the Lenovo Legion Go S.

Speaks to ``org.shadowblip.Output.ForceFeedback`` on the composite
device that InputPlumber creates for the Go S. We shell out to
``gdbus`` instead of pulling in a D-Bus Python dependency — gdbus is
always present on SteamOS and the rumble path is not latency-critical
enough to justify a native binding.

The subprocess env is **rebuilt minimal** rather than inherited from
``os.environ``. The plugin_loader process runs with only a handful of
PyInstaller vars (``_PYI_*``, ``LD_LIBRARY_PATH``); inheriting those
was breaking gdbus in two distinct ways at different points (libgio
mismatch from LD_LIBRARY_PATH; unclear interference from _PYI_*).
A clean env with just the basics avoids both.
"""

from __future__ import annotations

import os
import subprocess

from . import HapticBackend

DBUS_SERVICE = "org.shadowblip.InputPlumber"
DBUS_PATH = "/org/shadowblip/InputPlumber/CompositeDevice0"
DBUS_INTERFACE = "org.shadowblip.Output.ForceFeedback"


def _build_env() -> dict[str, str]:
    """Minimal env for the gdbus subprocess.

    ``USER`` is what polkit reads via ``subject.user``; the rule in
    ``/etc/polkit-1/rules.d/49-deckysense.rules`` authorises deck
    without ``auth_admin``. ``HOME`` and ``PATH`` keep gdbus happy.
    """
    return {
        "USER": "deck",
        "HOME": "/home/deck",
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        # Kept as a belt-and-suspenders: lets InputPlumber's own
        # polkit bypass kick in if it ever respects the caller's env.
        "INSECURE_DISABLE_POLKIT": "1",
    }


class InputPlumberAdapter(HapticBackend):
    """Talks to InputPlumber via the ``gdbus`` CLI."""

    def rumble(self, intensity: float) -> None:
        clamped = max(0.0, min(float(intensity), 1.0))
        self._call("Rumble", str(clamped))

    def stop(self) -> None:
        self._call("Stop")

    @staticmethod
    def _call(method: str, *args: str) -> None:
        cmd = [
            "/usr/bin/gdbus",
            "call",
            "--system",
            "--dest",
            DBUS_SERVICE,
            "--object-path",
            DBUS_PATH,
            "--method",
            f"{DBUS_INTERFACE}.{method}",
            *args,
        ]
        try:
            result = subprocess.run(
                cmd,
                env=_build_env(),
                capture_output=True,
                text=True,
                timeout=5,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"gdbus binary not found at /usr/bin/gdbus: {exc}"
            ) from exc
        if result.returncode != 0:
            err = (result.stderr or result.stdout).strip()
            raise RuntimeError(f"gdbus exit {result.returncode}: {err}")
