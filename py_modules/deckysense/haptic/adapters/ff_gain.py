"""Kernel FF_GAIN backend.

Switches InputPlumber to the ``xb360`` target (Xbox 360 controller
emulation) so that games see a standard evdev force-feedback device.
We then write ``FF_GAIN`` events directly to that device — the kernel
scales *every* force-feedback effect before passing it to the uinput
handler, so gain affects all game rumble transparently.

Balance is not available at the kernel level (FF_GAIN is a single
global scalar), but the preview path demonstrates it.
"""

from __future__ import annotations

import fcntl
import os
import struct
import subprocess
import threading
import time
from typing import final

import decky

from . import HapticBackend

# ── evdev constants ────────────────────────────────────────────────
EV_FF       = 0x15
FF_RUMBLE   = 0x50
FF_GAIN     = 0x60
FF_STATUS_MAX = 0x01
EVIOCSFF    = 0x40304580
EVIOCRMFF   = 0x40044581
EVIOCSGAIN  = 0x40024582
_FF_EFFECT_FMT = "<HhHHHHHxxHH28x"
_EVENT_FMT  = "<llHHi"

_VENDOR_MICROSOFT = 0x045e
_VENDOR_VALVE     = 0x28de


@final
class FFGainBackend(HapticBackend):
    """Switch to xb360 target and use kernel FF_GAIN for game rumble."""

    id = "ff_gain"
    name = "Kernel FF_GAIN"
    description = (
        "Switches InputPlumber to Xbox 360 controller emulation. "
        "Writes FF_GAIN at the kernel level so ALL game force-feedback "
        "is scaled by the gain slider. Balance is preview-only (kernel "
        "gain is a single global scalar). This is the most reliable "
        "way to affect game rumble from a Decky plugin."
    )
    features = frozenset({"gain", "game_gain"})

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._fd: int | None = None
        self._effect_id: int | None = None
        self._gain: float = 1.0
        self._switch_target()
        self._find_device()

    # ── identity ────────────────────────────────────────────────────

    # (class-level attributes above suffice)

    # ── public API ──────────────────────────────────────────────────

    def rumble(self, intensity: float, balance: float = 0.5) -> None:
        if self._fd is None:
            raise RuntimeError("FFGainBackend: no device fd")
        clamped = max(0.0, min(1.0, intensity))
        bal = max(0.0, min(1.0, balance))
        strong = round(0xFFFF * clamped * min(1.0, bal * 2.0))
        weak   = round(0xFFFF * clamped * min(1.0, (1.0 - bal) * 2.0))
        if self._effect_id is not None:
            try:
                fcntl.ioctl(self._fd, EVIOCRMFF, self._effect_id)
            except OSError:
                pass
            self._effect_id = None
        buf = bytearray(struct.pack(_FF_EFFECT_FMT, FF_RUMBLE, -1, 0, 0, 0, 500, 0, strong, weak))
        try:
            fcntl.ioctl(self._fd, EVIOCSFF, buf, True)
            self._effect_id = struct.unpack_from("<h", buf, 2)[0]
            ev = struct.pack(_EVENT_FMT, 0, 0, EV_FF, self._effect_id, 1)
            os.write(self._fd, ev)
        except OSError as exc:
            raise RuntimeError(f"FFGainBackend: rumble failed: {exc}") from exc

    def stop(self) -> None:
        if self._fd is not None and self._effect_id is not None:
            ev = struct.pack(_EVENT_FMT, 0, 0, EV_FF, self._effect_id, 0)
            try:
                os.write(self._fd, ev)
            except OSError:
                pass

    def set_kernel_gain(self, gain: float) -> None:
        clamped = max(0.0, min(1.0, float(gain)))
        with self._lock:
            self._gain = clamped
        if self._fd is not None:
            self._write_ff_gain(clamped)

    def set_balance(self, balance: float) -> None:
        pass  # Kernel FF_GAIN is global — no per-effect split.

    def close(self) -> None:
        fd = self._fd
        if fd is not None:
            try:
                self._write_ff_gain(1.0)  # reset
            except OSError:
                pass
            try:
                os.close(fd)
            except OSError:
                pass
            self._fd = None

    # ── target switching ────────────────────────────────────────────

    def _switch_target(self) -> None:
        """Tell InputPlumber to emit an Xbox 360 controller.

        We try gdbus first; if that fails we log a warning and let
        ``_find_device`` scan for whatever is available.
        """
        try:
            subprocess.run(
                [
                    "gdbus", "call", "--system",
                    "--dest", "org.shadowblip.InputPlumber",
                    "--object-path",
                    "/org/shadowblip/InputPlumber/CompositeDevice0",
                    "--method",
                    "org.shadowblip.Input.CompositeDevice.SetTargetDevices",
                    "['xb360']",
                ],
                capture_output=True,
                timeout=5,
                check=False,  # don't raise — we degrade gracefully
            )
        except FileNotFoundError:
            decky.logger.warning("FFGainBackend: gdbus not found; skipping target switch")
        except Exception as exc:
            decky.logger.warning("FFGainBackend: target switch failed: %s", exc)

    # ── device discovery ────────────────────────────────────────────

    def _find_device(self) -> None:
        """Scan /dev/input/event* for the xb360 virtual device.

        We first wait a short while for InputPlumber to create the
        new device after the target switch, then fall back to any
        FF-capable device.
        """
        time.sleep(0.5)  # give InputPlumber time to create the device
        import glob
        for path in sorted(
            glob.glob("/dev/input/event*"),
            key=lambda p: int(p.replace("/dev/input/event", "")),
        ):
            try:
                fd = os.open(path, os.O_RDWR)
            except OSError:
                continue
            name = self._query_name(fd)
            vid  = self._query_vendor(fd)
            # Xbox 360 / Xbox One / Microsoft controllers
            if vid == _VENDOR_MICROSOFT or "xbox" in name.lower() or "xpad" in name.lower():
                self._fd = fd
                decky.logger.info("FFGainBackend: found device %s (%s)", path, name)
                self._write_ff_gain(self._gain)
                return
            os.close(fd)
        # Fallback: grab any FF-capable device
        decky.logger.warning("FFGainBackend: no xb360 device found; scanning any FF device")
        for path in sorted(
            glob.glob("/dev/input/event*"),
            key=lambda p: int(p.replace("/dev/input/event", "")),
        ):
            try:
                fd = os.open(path, os.O_RDWR)
            except OSError:
                continue
            if self._probe_ff(fd):
                self._fd = fd
                name = self._query_name(fd)
                decky.logger.info("FFGainBackend: fallback device %s (%s)", path, name)
                self._write_ff_gain(self._gain)
                return
            os.close(fd)
        decky.logger.error("FFGainBackend: no FF-capable device found")

    # ── FF_GAIN writer ──────────────────────────────────────────────

    def _write_ff_gain(self, gain: float) -> None:
        if self._fd is None:
            return
        raw = round(0xFFFF * max(0.0, min(1.0, gain)))
        ev = struct.pack(_EVENT_FMT, 0, 0, EV_FF, FF_GAIN, raw)
        os.write(self._fd, bytes(ev))

    # ── helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _query_name(fd: int) -> str:
        EVIOCGNAME = 0x82004506
        buf = bytearray(256)
        try:
            fcntl.ioctl(fd, EVIOCGNAME, buf, True)
            return buf.split(b"\x00", 1)[0].decode("utf-8", errors="replace")
        except OSError:
            return ""

    @staticmethod
    def _query_vendor(fd: int) -> int:
        EVIOCGID = 0x80084502
        buf = bytearray(8)
        try:
            fcntl.ioctl(fd, EVIOCGID, buf, True)
            return struct.unpack_from("<H", buf, 2)[0]
        except OSError:
            return 0

    @staticmethod
    def _probe_ff(fd: int) -> bool:
        buf = bytearray(struct.pack(_FF_EFFECT_FMT, FF_RUMBLE, -1, 0, 0, 0, 10, 0, 1, 1))
        try:
            fcntl.ioctl(fd, EVIOCSFF, buf, True)
            eid = struct.unpack_from("<h", buf, 2)[0]
            ev = struct.pack(_EVENT_FMT, 0, 0, EV_FF, eid, 0)
            os.write(fd, ev)
            return True
        except OSError:
            return False
