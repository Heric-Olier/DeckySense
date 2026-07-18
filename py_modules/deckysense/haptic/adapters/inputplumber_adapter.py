"""InputPlumber D-Bus adapter for the Lenovo Legion Go S.

Speaks to ``org.shadowblip.Output.ForceFeedback`` on the composite
device that InputPlumber creates for the Go S. We shell out to
``gdbus`` instead of pulling in a D-Bus Python dependency — gdbus is
always present on SteamOS and the rumble path is not latency-critical
enough to justify a native binding.

Two environment quirks of the plugin_loader process need to be handled:

- ``LD_LIBRARY_PATH`` is set to Decky's bundled library directory and
  breaks the system ``gdbus`` (it loads the wrong libgio/libglib and
  exits 1 silently). Stripped before the subprocess runs.
- The plugin_loader runs without an active logind session, so polkit
  treats it as a non-interactive client and refuses to authorise
  ``org.shadowblip.Output.ForceFeedback.Rumble``. InputPlumber respects
  ``INSECURE_DISABLE_POLKIT=1`` as an escape hatch for exactly this
  kind of caller; we set it on the subprocess env.

  The "INSECURE" name is a warning, not a blocker: this plugin only
  runs on the user's own device and only this subprocess is affected.
  The cleaner long-term fix is to add the ``deck`` user to the
  ``inputplumber`` group (the polkit rule already grants its members
  full access). For now, this lets Haptic Studio work out of the box.
"""

from __future__ import annotations

import os
import subprocess

from . import HapticBackend

DBUS_SERVICE = "org.shadowblip.InputPlumber"
DBUS_PATH = "/org/shadowblip/InputPlumber/CompositeDevice0"
DBUS_INTERFACE = "org.shadowblip.Output.ForceFeedback"


def _build_env() -> dict[str, str]:
    env = dict(os.environ)
    env.pop("LD_LIBRARY_PATH", None)
    env["INSECURE_DISABLE_POLKIT"] = "1"
    return env


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

