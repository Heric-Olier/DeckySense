#!/usr/bin/env bash
# DeckSense Phase 0 — second-round probe.
#
# Identifies which hidraw device is the gamepad, what driver claims it,
# and what D-Bus interfaces InputPlumber exposes for rumble control.
# Read-only; safe to run on the device.
set -uo pipefail

section() { printf '\n===== %s =====\n' "$1"; }

section "/proc/bus/input/devices (full)"
cat /proc/bus/input/devices 2>/dev/null

section "/sys/bus/hid/drivers (loaded HID drivers and their bound devices)"
for d in /sys/bus/hid/drivers/*/; do
  [[ -d "$d" ]] || continue
  name=$(basename "$d")
  echo "--- $name ---"
  # Entries that are symlinks to actual devices (skip '.', '..', 'module', 'bind', 'unbind', 'uevent').
  ls -la "$d" 2>/dev/null | awk 'NR>1 && $0 !~ /module|uevent|bind|unbind|^total|^d/'
done

section "/sys/class/input"
ls -la /sys/class/input/ 2>/dev/null | head -40

section "udevadm info for each /dev/hidraw*"
for h in /dev/hidraw*; do
  [[ -e "$h" ]] || continue
  echo "--- $h ---"
  udevadm info --query=property --name="$h" 2>/dev/null | head -25
  echo
done

section "InputPlumber D-Bus service discovery (busctl list filtered)"
busctl list 2>/dev/null | grep -iE 'input|plumber|shadowblip|gamepad' | head -20

section "InputPlumber D-Bus introspection at root"
gdbus introspect --system --dest org.shadowblip.InputPlumber --object-path /org/shadowblip/InputPlumber 2>&1 | head -60

section "InputPlumber config / data files"
ls -la /etc/inputplumber/ 2>/dev/null || echo "(no /etc/inputplumber)"
ls -la /usr/share/inputplumber/ 2>/dev/null || echo "(no /usr/share/inputplumber)"
ls -la /etc/systemd/system/inputplumber* 2>/dev/null || true

section "evdev devices via libevdev"
for ev in /dev/input/event*; do
  [[ -e "$ev" ]] || continue
  echo "--- $ev ---"
  udevadm info --query=property --name="$ev" 2>/dev/null | grep -E 'ID_(NAME|INPUT|VENDOR|MODEL)' | head -15
  echo
done

section "done"
