"""System status service.

Read-only snapshot of the pieces the UI must show to stay honest:
the controller's input mode (sysfs, exposed by hid-lenovo-go-s) and the
force-feedback enabled flag (InputPlumber D-Bus). Every getter is
fail-safe: missing pieces come back as None and the UI renders
"unknown" instead of crashing.
"""

from __future__ import annotations

import glob
import os
import subprocess
from typing import Any

import decky

_CTRL_GLOB = "/sys/bus/hid/devices/*1A86:E310.*"

_DBUS_BASE = [
    "gdbus",
    "call",
    "--system",
    "--dest",
    "org.shadowblip.InputPlumber",
    "--object-path",
    "/org/shadowblip/InputPlumber/CompositeDevice0",
]
_FF_IFACE = "org.shadowblip.Output.ForceFeedback"
_PROPS = "org.freedesktop.DBus.Properties"


def get_controller_info() -> dict[str, Any]:
    """Input mode of the physical controller, from hid-lenovo-go-s sysfs.

    hid-lenovo-go-s exposes gamepad/mode (xinput|dinput) and os_mode per
    HID device. There may be several instances after re-enumerations, so
    take the first one that actually has a gamepad dir.
    """
    try:
        for dev in sorted(glob.glob(_CTRL_GLOB)):
            mode_path = os.path.join(dev, "gamepad", "mode")
            if not os.path.exists(mode_path):
                continue
            with open(mode_path, encoding="utf-8") as fh:
                mode = fh.read().strip() or None
            os_mode = None
            os_path = os.path.join(dev, "os_mode")
            if os.path.exists(os_path):
                with open(os_path, encoding="utf-8") as fh:
                    os_mode = fh.read().strip() or None
            return {"mode": mode, "os_mode": os_mode, "sysfs": dev}
    except OSError as e:
        decky.logger.warning(f"[status] controller read failed: {e}")
    return {"mode": None, "os_mode": None, "sysfs": None}


def _gdbus(*args: str) -> tuple[int, str]:
    proc = subprocess.run(
        [*_DBUS_BASE, "--method", *args],
        capture_output=True,
        text=True,
        timeout=5,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def get_ff_enabled() -> bool | None:
    """True/False when InputPlumber answers, None when unavailable."""
    try:
        code, out = _gdbus(_PROPS + ".Get", _FF_IFACE, "Enabled")
        if code != 0:
            return None
        low = out.lower()
        if "true" in low:
            return True
        if "false" in low:
            return False
        return None
    except Exception as e:  # noqa: BLE001
        decky.logger.warning(f"[status] FF get failed: {e}")
        return None


def set_ff_enabled(value: bool) -> dict[str, Any]:
    """Enable/disable system force feedback.

    The D-Bus property is a variant, so gdbus needs GVariant text
    (<true>/<false>) — plain true/false fails with "can not parse as
    value of type 'v'". Returns the read-back state, not the request.
    """
    arg = "<true>" if value else "<false>"
    try:
        code, out = _gdbus(_PROPS + ".Set", _FF_IFACE, "Enabled", arg)
        if code != 0:
            decky.logger.warning(f"[status] FF set failed: {out.strip()[:200]}")
    except Exception as e:  # noqa: BLE001
        decky.logger.warning(f"[status] FF set failed: {e}")
    return {"enabled": get_ff_enabled()}
