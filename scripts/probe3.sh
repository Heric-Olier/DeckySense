#!/usr/bin/env bash
# DeckySense Phase 0 — third probe.
# Deep introspection of InputPlumber D-Bus and driver config files.
# Read-only.
set -uo pipefail

section() { printf '\n===== %s =====\n' "$1"; }

section "InputPlumber D-Bus: GetManagedObjects (compact)"
gdbus call --system --dest org.shadowblip.InputPlumber \
  --object-path /org/shadowblip/InputPlumber \
  --method org.freedesktop.DBus.ObjectManager.GetManagedObjects 2>&1 | head -200

section "InputPlumber D-Bus: introspect /Manager/Devices path"
gdbus introspect --system --dest org.shadowblip.InputPlumber \
  --object-path /org/shadowblip/InputPlumber/Manager/Devices \
  2>&1 | head -80

section "InputPlumber device definitions in /usr/share/inputplumber/devices"
ls /usr/share/inputplumber/devices/ 2>/dev/null
echo "---"
echo "Files mentioning 'legion' or 'lenovo' inside InputPlumber data:"
grep -rliE 'legion|lenovo' /usr/share/inputplumber/ 2>/dev/null | head -10

section "Gamepad native event2 ff effect files"
NATIVE_SYSFS=/sys/devices/pci0000:00/0000:00:08.1/0000:c3:00.4/usb3/3-1/3-1:1.1/input/input11
ls -la "${NATIVE_SYSFS}/event2/device/" 2>/dev/null | head -20
echo "--- force feedback subdirs ---"
find "${NATIVE_SYSFS}/" -maxdepth 3 -iname '*ff*' -o -iname '*effect*' 2>/dev/null | head -20
echo "--- input11 capabilities ---"
cat "${NATIVE_SYSFS}/capabilities/ff" 2>/dev/null
echo
echo "--- input11 name ---"
cat "${NATIVE_SYSFS}/name" 2>/dev/null
echo
echo "--- input11 uniq/phys ---"
cat "${NATIVE_SYSFS}/uniq" 2>/dev/null
echo
cat "${NATIVE_SYSFS}/phys" 2>/dev/null

section "Permissions on hidraw devices potentially relevant to rumble"
for h in /dev/hidraw0 /dev/hidraw2 /dev/hidraw3 /dev/hidraw4 /dev/hidraw5 /dev/inputplumber/by-hidden/hidraw4 /dev/inputplumber/by-hidden/hidraw5; do
  printf '%s -> ' "$h"
  ls -la "$h" 2>&1 | head -1
done

section "InputPlumber hidraw symlink tree"
ls -la /dev/inputplumber/ 2>/dev/null
ls -la /dev/inputplumber/by-hidden/ 2>/dev/null

section "InputPlumber version / binary"
inputplumber --version 2>&1 | head -3 || true
inputplumberctl --version 2>&1 | head -3 || true

section "done"
