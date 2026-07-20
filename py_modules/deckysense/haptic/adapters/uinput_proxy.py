"""Uinput proxy device that intercepts force-feedback effects.

Creates a virtual ``/dev/input/event*`` device via uinput, grabs the
real gamepad, and proxies all input events through.  When a game uploads
a ``FF_RUMBLE`` effect, the proxy applies the plugin's gain and balance
before forwarding it to the real hardware.

This is the only way to make gain/balance affect **all** rumble on the
device — not just the plugin's own preview — because game processes
send ``EVIOCSFF`` / ``EV_FF`` to their own file descriptor and there is
no kernel API to intercept those from a different fd.
"""

from __future__ import annotations

import ctypes
import errno
import fcntl
import os
import select
import struct
import threading
from typing import final

from . import HapticBackend

# ── uinput ioctl constants ──────────────────────────────────────────
# All are _IOW('U', nr, int)  →  (1 << 30) | (4 << 16) | (ord('U') << 8) | nr

UI_SET_EVBIT     = 0x40045564  # nr 100
UI_SET_KEYBIT    = 0x40045565  # nr 101
UI_SET_RELBIT    = 0x40045566  # nr 102
UI_SET_ABSBIT    = 0x40045567  # nr 103
UI_SET_FFBIT     = 0x4004556C  # nr 108
UI_DEV_CREATE    = 0x5501      # _IO('U', 1)
UI_DEV_DESTROY   = 0x5502      # _IO('U', 2)

# ── evdev constants (duplicated to keep this file self-contained) ───
EV_SYN           = 0x00
EV_KEY           = 0x01
EV_REL           = 0x02
EV_ABS           = 0x03
EV_FF            = 0x15
EV_FF_STATUS     = 0x17
FF_RUMBLE        = 0x50
FF_GAIN          = 0x60
EVIOCGRAB        = 0x40044546  # _IOW('E', 0x46, int) — "F"=0x46
EVIOCSFF         = 0x40304580
EVIOCRMFF        = 0x40044581
SYN_REPORT       = 0

# ── struct input_event (16 bytes) ───────────────────────────────────
# struct input_event {
#     struct timeval time;  // 2 × __s64 = 16 bytes
#     __u16 type;
#     __u16 code;
#     __s32 value;
# };
_INPUT_EVENT_FMT = "<llHHi"
_INPUT_EVENT_SIZE = struct.calcsize(_INPUT_EVENT_FMT)

# ── struct ff_effect (48 bytes, x86_64) ────────────────────────────
_FF_EFFECT_FMT = "<HhHHHHHxxHH28x"
_FF_EFFECT_FMT_BODY = _FF_EFFECT_FMT.lstrip("<")
_FF_EFFECT_SIZE = struct.calcsize(_FF_EFFECT_FMT)

# struct uinput_ff_upload
#     __u32 request_id;
#     __s32 retval;
#     struct ff_effect effect;   // 48
#     struct ff_effect old;      // 48
_FF_UPLOAD_FMT = "<Ii" + _FF_EFFECT_FMT_BODY + _FF_EFFECT_FMT_BODY
_FF_UPLOAD_SIZE = struct.calcsize(_FF_UPLOAD_FMT)
# Wire format: __u32 request_id; __s32 retval; ff_effect effect; ff_effect old;
# On x86_64, __u32 + __s32 = 8 bytes, then ff_effect (48 bytes, 4-byte aligned).
# Total: 4 + 4 + 48 + 48 = 104 bytes.
_FF_UPLOAD_WIRE_SIZE = 4 + 4 + _FF_EFFECT_SIZE * 2

# struct uinput_ff_erase
#     __u32 request_id;
#     __s32 retval;
#     __s32 effect_id;
_FF_ERASE_FMT = "<Iii"
_FF_ERASE_SIZE = struct.calcsize(_FF_ERASE_FMT)

# ── uinput_user_dev layout ──────────────────────────────────────────
# struct uinput_user_dev {
#     char name[80];                       // 0
#     __u16 bustype;                       // 80
#     __u16 vendor;                        // 82
#     __u16 product;                       // 84
#     __u16 version;                       // 86
#     __s32 ff_effects_max;                // 88
#     __s32 absmax[ABS_CNT];              // 92   (ABS_CNT = 0x3f)
#     __s32 absmin[ABS_CNT];              // 344
#     __s32 absfuzz[ABS_CNT];             // 596
#     __s32 absflat[ABS_CNT];             // 848
# };                                       // total = 1100
_ABS_CNT = 0x3F
_UINPUT_USER_DEV_SIZE = 80 + 8 + 4 + 4 * _ABS_CNT * 4


def _find_gamepad() -> tuple[int, str]:
    """Open the first /dev/input/event* that supports FF_RUMBLE.

    Returns ``(fd, path)``.
    """
    import glob
    for path in sorted(glob.glob("/dev/input/event*"),
                       key=lambda p: int(p.replace("/dev/input/event", ""))):
        try:
            fd = os.open(path, os.O_RDWR)
        except OSError:
            continue
        try:
            buf = bytearray(struct.pack(_FF_EFFECT_FMT,
                                        FF_RUMBLE, -1, 0, 0, 0, 500, 0, 1, 1))
            fcntl.ioctl(fd, EVIOCSFF, buf, True)
            eid = struct.unpack_from("<h", buf, 2)[0]
            ev = struct.pack(_INPUT_EVENT_FMT, 0, 0, EV_FF, eid, 0)
            os.write(fd, ev)
            return fd, path
        except OSError:
            os.close(fd)
            continue
    raise RuntimeError("no /dev/input/event* device supports force-feedback")


@final
class UinputProxy(HapticBackend):
    """Grab the real gamepad, create a uinput proxy, intercept FF effects.

    Usage
    -----
    Create a single instance and keep it alive for the lifetime of the
    plugin.  Call ``close()`` to release the real device and destroy the
    virtual device.

    Thread-safety
    -------------
    ``rumble()``, ``stop()``, ``set_kernel_gain()`` are called from the
    asyncio executor thread.  The proxy spawns its own reader thread for
    the input-event loop.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._gain: float = 1.0
        self._balance: float = 0.5

        # Real device
        self._real_fd: int | None = None
        self._real_path: str = ""

        # Uinput device
        self._uinput_fd: int | None = None

        # Reader thread
        self._running = False
        self._thread: threading.Thread | None = None

        self._last_effect_id: int = -1

        self._open_devices()

    # ── public API ──────────────────────────────────────────────────

    def rumble(self, intensity: float, balance: float = 0.5) -> None:
        """Play a preview rumble on the real device (bypass proxy).

        Used by the plugin's own preview feature.
        """
        with self._lock:
            bal = balance if balance is not None else self._balance
        self._play_effect(intensity, bal)

    def stop(self) -> None:
        """Stop any currently playing preview effect."""
        self._stop_effect()

    def set_kernel_gain(self, gain: float) -> None:
        """Store the gain that will be applied to intercepted FF effects.

        The actual gain is applied during ``UI_FF_UPLOAD`` handling.
        """
        with self._lock:
            self._gain = max(0.0, min(gain, 1.0))

    def set_balance(self, balance: float) -> None:
        """Store the balance that will be applied to intercepted FF."""
        with self._lock:
            self._balance = max(0.0, min(balance, 1.0))

    def close(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None
        uifd = self._uinput_fd
        if uifd is not None:
            try:
                fcntl.ioctl(uifd, UI_DEV_DESTROY)
            except OSError:
                pass
            try:
                os.close(uifd)
            except OSError:
                pass
            self._uinput_fd = None
        rfd = self._real_fd
        if rfd is not None:
            try:
                fcntl.ioctl(rfd, EVIOCGRAB, 0)  # ungrab
            except OSError:
                pass
            try:
                os.close(rfd)
            except OSError:
                pass
            self._real_fd = None

    # ── internal helpers ────────────────────────────────────────────

    def _open_devices(self) -> None:
        """Open real device (grab) and create uinput proxy."""
        real_fd, real_path = _find_gamepad()
        self._real_fd = real_fd
        self._real_path = real_path

        # Grab exclusive access
        fcntl.ioctl(real_fd, EVIOCGRAB, 1)

        # Query device properties for uinput setup
        name = self._query_name(real_fd)
        bustype, vendor, product, version = self._query_id(real_fd)

        # Create uinput
        uifd = os.open("/dev/uinput", os.O_WRONLY | os.O_NONBLOCK)
        self._uinput_fd = uifd

        # Enable event types
        for ev in (EV_KEY, EV_REL, EV_ABS, EV_FF, EV_FF_STATUS, EV_SYN):
            fcntl.ioctl(uifd, UI_SET_EVBIT, ev)

        # Enable FF_RUMBLE
        fcntl.ioctl(uifd, UI_SET_FFBIT, FF_RUMBLE)
        fcntl.ioctl(uifd, UI_SET_FFBIT, FF_GAIN)

        # Enable key bits from real device
        self._copy_bits(real_fd, uifd, EV_KEY, UI_SET_KEYBIT)
        self._copy_bits(real_fd, uifd, EV_REL, UI_SET_RELBIT)

        # For ABS we need the bits both for enabling and for populating
        # the abs arrays in uinput_user_dev.
        abs_bits = self._query_ev_bits(real_fd, EV_ABS)
        for code in range(len(abs_bits) * 8):
            if abs_bits[code // 8] & (1 << (code % 8)):
                try:
                    fcntl.ioctl(uifd, UI_SET_ABSBIT, code)
                except OSError:
                    pass

        # Write uinput_user_dev
        dev_buf = bytearray(_UINPUT_USER_DEV_SIZE)
        name_bytes = (name[:79].encode("utf-8", errors="replace") + b"\x00")[:80]
        dev_buf[0:80] = name_bytes
        struct.pack_into("<HHHH", dev_buf, 80, bustype, vendor, product, version)
        struct.pack_into("<i", dev_buf, 88, 16)
        self._fill_abs_info(real_fd, dev_buf, abs_bits)
        os.write(uifd, bytes(dev_buf))

        # Create the device
        fcntl.ioctl(uifd, UI_DEV_CREATE)

        # Start reader thread
        self._running = True
        self._thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._thread.start()

    def _reader_loop(self) -> None:
        """Read events from real device → forward to uinput.

        Also handle FF upload/erase requests from uinput.
        """
        poll = select.poll()
        poll.register(self._real_fd, select.POLLIN)
        poll.register(self._uinput_fd, select.POLLIN)

        while self._running:
            try:
                events = poll.poll(timeout=500)
            except OSError:
                break

            for fd, _event in events:
                if fd == self._real_fd and self._real_fd is not None:
                    self._forward_input()
                elif fd == self._uinput_fd and self._uinput_fd is not None:
                    self._handle_uinput_event()

    def _forward_input(self) -> None:
        """Read one or more input events from real device and write to uinput."""
        try:
            buf = os.read(self._real_fd, _INPUT_EVENT_SIZE * 32)
        except OSError:
            return
        if self._uinput_fd is not None:
            try:
                os.write(self._uinput_fd, buf)
            except OSError:
                pass

    def _handle_uinput_event(self) -> None:
        """Process FF upload/erase requests from the uinput fd.

        The kernel writes ``uinput_ff_upload`` (104 bytes) or
        ``uinput_ff_erase`` (12 bytes) structs atomically to the fd when
        a client uploads or erases an effect.  We distinguish them by
        read size.
        """
        try:
            data = os.read(self._uinput_fd, _FF_UPLOAD_WIRE_SIZE)
            if len(data) == _FF_ERASE_SIZE:
                (_req_id, _retval, effect_id) = struct.unpack_from(
                    _FF_ERASE_FMT, data
                )
                request_id = struct.unpack_from("<I", data)[0]
                self._handle_erase(request_id, effect_id)
            elif len(data) == _FF_UPLOAD_WIRE_SIZE:
                self._handle_upload(data)
            # else: partial read or unknown struct — skip
        except OSError:
            pass

    def _handle_upload(self, data: bytes) -> None:
        """Intercept a FF upload, apply gain/balance, forward to real device."""
        # Parse the upload struct
        parts = struct.unpack_from(_FF_UPLOAD_FMT, data)
        request_id = parts[0]
        retval = parts[1]
        # parts[2:14] = effect struct fields
        # parts[14:26] = old effect struct fields
        eff_type = parts[2]
        eff_id = parts[3]

        if eff_type != FF_RUMBLE:
            # Forward unchanged
            self._relay_upload(request_id, data)
            return

        # Apply gain and balance
        with self._lock:
            gain = self._gain
            balance = self._balance

        strong_mag = parts[2 + 7]  # offset 7 in ff_effect = u.rumble.strong_magnitude
        weak_mag = parts[2 + 8]   # offset 8 = u.rumble.weak_magnitude

        # Apply gain (kernel-style: multiply and clamp)
        strong_mag = min(0xFFFF, round(strong_mag * gain * min(1.0, balance * 2.0)))
        weak_mag = min(0xFFFF, round(weak_mag * gain * min(1.0, (1.0 - balance) * 2.0)))

        if self._real_fd is None:
            # No real device — reply with error
            resp = struct.pack(_FF_UPLOAD_FMT,
                               request_id, -errno.ENODEV,
                               *parts[2:14], *parts[14:26])
            os.write(self._uinput_fd, resp)
            return

        # Forward modified effect to real device
        real_effect = bytearray(struct.pack(_FF_EFFECT_FMT,
                                            eff_type, -1, 0, 0, 0, 500, 0,
                                            strong_mag, weak_mag))
        try:
            fcntl.ioctl(self._real_fd, EVIOCSFF, real_effect, True)
            real_eff_id = struct.unpack_from("<h", real_effect, 2)[0]
        except OSError:
            real_eff_id = -1

        # Build response for the client
        # The client expects back the (possibly modified) effect with the
        # effect_id filled in by the kernel.
        new_effect = list(parts[2:14])
        new_effect[1] = real_eff_id  # id field
        resp = struct.pack(_FF_UPLOAD_FMT,
                           request_id, 0 if real_eff_id >= 0 else -errno.EIO,
                           *new_effect, *parts[14:26])

        try:
            os.write(self._uinput_fd, resp)
        except OSError:
            pass

    def _handle_erase(self, request_id: int, effect_id: int) -> None:
        """Forward erase to real device."""
        if self._real_fd is not None:
            try:
                fcntl.ioctl(self._real_fd, EVIOCRMFF, effect_id)
            except OSError:
                pass

        resp = struct.pack("<Iii", request_id, 0, effect_id)
        try:
            os.write(self._uinput_fd, resp)
        except OSError:
            pass

    def _relay_upload(self, request_id: int, data: bytes) -> None:
        """Relay a non-FF_RUMBLE upload to the real device unchanged."""
        # We need to forward the effect.  Re-parse the effect part.
        eff_type = struct.unpack_from("<H", data, 8)[0]
        eff_id = struct.unpack_from("<h", data, 10)[0]

        if self._real_fd is None:
            resp = struct.pack(_FF_UPLOAD_FMT,
                               request_id, -errno.ENODEV,
                               *(0,) * 12, *(0,) * 12)
            os.write(self._uinput_fd, resp)
            return

        # Extract effect from data (offset 8)
        eff_data = data[8:8 + _FF_EFFECT_SIZE]
        real_buf = bytearray(eff_data)
        struct.pack_into("<h", real_buf, 2, -1)  # set id to -1 for new effect
        try:
            fcntl.ioctl(self._real_fd, EVIOCSFF, real_buf, True)
            real_eff_id = struct.unpack_from("<h", real_buf, 2)[0]
        except OSError:
            real_eff_id = -1

        new_eff_data = bytearray(eff_data)
        struct.pack_into("<h", new_eff_data, 2, real_eff_id)
        resp = struct.pack(_FF_UPLOAD_FMT,
                           request_id, 0 if real_eff_id >= 0 else -errno.EIO,
                           *struct.unpack_from(_FF_EFFECT_FMT, new_eff_data),
                           *struct.unpack_from(_FF_EFFECT_FMT, data[8 + _FF_EFFECT_SIZE:]))
        try:
            os.write(self._uinput_fd, resp)
        except OSError:
            pass

    def _play_effect(self, intensity: float, balance: float) -> None:
        """Upload and play an FF effect on the real device (preview)."""
        if self._real_fd is None:
            return
        clamped = max(0.0, min(1.0, intensity))
        bal = max(0.0, min(1.0, balance))
        strong = round(0xFFFF * clamped * min(1.0, bal * 2.0))
        weak = round(0xFFFF * clamped * min(1.0, (1.0 - bal) * 2.0))

        # Remove previous
        try:
            fcntl.ioctl(self._real_fd, EVIOCRMFF, self._last_effect_id)
        except OSError:
            pass
        self._last_effect_id = -1

        buf = bytearray(struct.pack(_FF_EFFECT_FMT, FF_RUMBLE, -1, 0, 0, 0, 500, 0, strong, weak))
        try:
            fcntl.ioctl(self._real_fd, EVIOCSFF, buf, True)
            self._last_effect_id = struct.unpack_from("<h", buf, 2)[0]
            play = struct.pack(_INPUT_EVENT_FMT, 0, 0, EV_FF, self._last_effect_id, 1)
            os.write(self._real_fd, play)
        except OSError:
            pass

    def _stop_effect(self) -> None:
        if self._real_fd is None:
            return
        if self._last_effect_id >= 0:
            ev = struct.pack(_INPUT_EVENT_FMT, 0, 0, EV_FF, self._last_effect_id, 0)
            try:
                os.write(self._real_fd, ev)
            except OSError:
                pass

    # ── device info helpers ─────────────────────────────────────────

    @staticmethod
    def _query_name(fd: int) -> str:
        """Read the device name via EVIOCGNAME."""
        EVIOCGNAME = 0x82004506  # _IOWR('E', 6, char[256]) — actually _IOC(_IOC_READ, ...)
        name_buf = bytearray(256)
        try:
            fcntl.ioctl(fd, EVIOCGNAME, name_buf, True)
            return name_buf.split(b"\x00", 1)[0].decode("utf-8", errors="replace")
        except OSError:
            return "DeckySense Haptic Proxy"

    @staticmethod
    def _query_id(fd: int) -> tuple[int, int, int, int]:
        """Read the device's bus/vendor/product/version."""
        EVIOCGID = 0x80084502  # _IOWR('E', 2, struct input_id)
        id_buf = bytearray(8)
        try:
            fcntl.ioctl(fd, EVIOCGID, id_buf, True)
            return struct.unpack_from("<HHHH", id_buf, 0)
        except OSError:
            return (0, 0, 0, 0)

    @staticmethod
    def _query_ev_bits(fd: int, ev_type: int) -> bytearray:
        buf = bytearray(256)
        nr = 0x20 + ev_type
        ioc = (2 << 30) | (len(buf) << 16) | (ord("E") << 8) | nr
        try:
            fcntl.ioctl(fd, ioc, buf, True)
        except OSError:
            pass
        return buf

    @staticmethod
    def _fill_abs_info(real_fd: int, dev_buf: bytearray, abs_bits: bytearray) -> None:
        for code in range(_ABS_CNT):
            if not (abs_bits[code // 8] & (1 << (code % 8))):
                continue
            # EVIOCGABS(code) = _IOR('E', 0x40 + code, struct input_absinfo)
            ioc = (2 << 30) | (24 << 16) | (ord("E") << 8) | (0x40 + code)
            buf = bytearray(24)
            try:
                fcntl.ioctl(real_fd, ioc, buf, True)
                _minimum, _maximum, _fuzz, _flat = struct.unpack_from(
                    "<iiii", buf, 4
                )  # skip 'value' at offset 0
                off_max = 92
                off_min = 92 + _ABS_CNT * 4
                off_fuzz = 92 + _ABS_CNT * 8
                off_flat = 92 + _ABS_CNT * 12
                struct.pack_into("<i", dev_buf, off_max + code * 4, _maximum)
                struct.pack_into("<i", dev_buf, off_min + code * 4, _minimum)
                struct.pack_into("<i", dev_buf, off_fuzz + code * 4, _fuzz)
                struct.pack_into("<i", dev_buf, off_flat + code * 4, _flat)
            except OSError:
                pass

    @staticmethod
    def _copy_bits(src_fd: int, dst_fd: int, ev_type: int, set_ioctl: int) -> None:
        ev_bits = UinputProxy._query_ev_bits(src_fd, ev_type)
        for bit in range(len(ev_bits) * 8):
            if ev_bits[bit // 8] & (1 << (bit % 8)):
                try:
                    fcntl.ioctl(dst_fd, set_ioctl, bit)
                except OSError:
                    pass
