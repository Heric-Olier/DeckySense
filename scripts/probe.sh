#!/usr/bin/env bash
# DeckySense Phase 0 hardware probe.
#
# Read-only inspection of the system to figure out what rumble / haptic
# access paths are available on this device. Safe to run on the device:
# it does not write to anything.
#
# Usage on the device (desktop mode or SSH):
#   curl -fsSL https://raw.githubusercontent.com/Heric-Olier/deckysense/main/scripts/probe.sh | bash
# or:
#   bash probe.sh > probe-output.txt 2>&1
#
# Paste the full output back so it can be analysed.
set -uo pipefail

section() {
  printf '\n===== %s =====\n' "$1"
}

section "uname"
uname -a

section "/etc/os-release"
cat /etc/os-release 2>/dev/null

section "/dev/hidraw*"
ls -la /dev/hidraw* 2>/dev/null || echo "(none)"

section "lsusb (lenovo/legion)"
lsusb 2>/dev/null | grep -iE 'lenovo|legion' || echo "(none)"

section "/proc/bus/input/devices (filtered to lenovo/legion)"
awk '
  /lenovo|legion/ { found=1 }
  /^$/ { found=0 }
  found { print }
' /proc/bus/input/devices 2>/dev/null || echo "(unavailable)"

section "sysfs entries matching lenovo/legion/rumble/vibrat/haptic"
find /sys/devices -maxdepth 8 \( \
  -iname '*lenovo*' -o \
  -iname '*legion*' -o \
  -iname '*rumble*' -o \
  -iname '*vibrat*' -o \
  -iname '*haptic*' \
\) 2>/dev/null | head -40 || echo "(none)"

section "loaded modules (lenovo/hid filtered)"
lsmod 2>/dev/null | grep -iE 'lenovo|hid_' || echo "(none)"

section "modinfo hid_lenovo_go"
modinfo hid_lenovo_go 2>&1 | head -15

section "lenovo module files in /lib/modules"
find "/lib/modules/$(uname -r)" -iname '*lenovo*' 2>/dev/null || echo "(none)"

section "inputplumber service"
systemctl status inputplumber --no-pager 2>&1 | head -8 || echo "(not found)"
command -v inputplumberctl >/dev/null 2>&1 && {
  inputplumberctl --version 2>&1 || true
  echo "--- inputplumberctl list-devices ---"
  inputplumberctl list-devices 2>&1 | head -30 || true
}

section "hhd (Handheld Daemon)"
systemctl status hhd --no-pager 2>&1 | head -8 || echo "(not found)"

section "Steam processes"
ps -A 2>/dev/null | grep -i steam | head -5 || echo "(steam not running)"

section "done"
