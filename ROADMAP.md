# Roadmap

The roadmap mirrors the phases of the internal Software Design
Document. Each phase has a clear exit criterion. Items marked
**Blocking** must be resolved before later phases can commit to a
specific implementation.

Statuses: `Not started` · `In progress` · `Blocked` · `Done`.

---

## Phase 0 — Hardware validation  *(Blocking)*

**Status:** Done

Validate the technical assumptions on a real Lenovo Legion Go S before
writing real features. All items are binary: confirmed or not confirmed.

- [x] Confirm the SteamOS kernel version shipped on the Legion Go S and
      whether it includes `hid-lenovo-go-s` (or equivalent), or whether
      everything routes through InputPlumber today.
      *Confirmed: SteamOS 3.8.23 / kernel 6.16.12 ships `hid_lenovo_go_s`
      already loaded. InputPlumber is the active input manager.*
- [x] Enumerate which sysfs / `/dev/hidraw*` nodes the controller exposes
      for rumble, and which value ranges they accept (intensity only, or
      waveform / frequency too).
      *Confirmed: rumble path is InputPlumber D-Bus
      `org.shadowblip.Output.ForceFeedback.Rumble(double)` at
      `/org/shadowblip/InputPlumber/CompositeDevice0`. Value is a 0.0–1.0
      intensity float. hidraw5 (gamepad) is exclusively owned by
      InputPlumber; sysfs has no rumble nodes.*
- [x] Test Steam Input's `TriggerVibration` / `TriggerVibrationExtended`
      against the device to determine whether Steam mediates rumble or a
      direct path exists outside the Steam client.
      *Partially answered: Steam sees only the virtual `deck-uhid`
      gamepad, so Steam Input always mediates. Direct interception
      between Steam and the kernel is not feasible from a Decky plugin;
      out of scope for MVP.*
- [x] Profile the physical motor: dead-zone, saturation point, response
      latency. These numbers feed directly into the Haptic Studio
      response curve.
      *Confirmed via a 0.05–1.0 sweep: gradual response across the
      range, no obvious dead-zone or saturation knee. Fine calibration
      (curve shape, "punch" envelope) is deferred into Haptic Studio's
      own UI.*

**Exit criterion:** every item above is confirmed or refuted on real
hardware, and the chosen haptic backend path documented in `DEVLOG.md`.
— **met.**

---

## Phase 1 — Display Studio MVP

**Status:** Not started

- [ ] Gamescope filter wrapper (saturation, contrast, sharpness, gamma,
      color temperature).
- [ ] Built-in presets: Sharp, Pixel Art, OLED-like.
- [ ] Confirmation timer that auto-reverts changes if the user does not
      confirm (prevents an unreadable screen from sticking).
- [ ] Settings persistence.

**Exit criterion:** the three presets apply and revert cleanly via the
Quick Access menu, with the confirmation timer enforced.

---

## Phase 2 — Haptic Studio MVP

**Status:** Not started — *depends on Phase 0*

- [ ] Haptic backend abstraction (`HapticBackend` interface).
- [ ] Legion Go S implementation following the path confirmed in
      Phase 0 (sysfs / hidraw / InputPlumber).
- [ ] Global gain control.
- [ ] Basic response curve (remap the motor's useful range).

**Exit criterion:** gain and curve changes are observable on the
device, with values persisted and applied on plugin (re)load.

---

## Phase 3 — Game Profiles

**Status:** Not started

- [ ] AppId detection (same mechanism used by other ecosystem plugins).
- [ ] Preset application on game change (Display + Haptic combined).
- [ ] Profile management UI (list, edit, duplicate, delete).

**Exit criterion:** launching a game with a stored profile applies the
expected Display and Haptic settings without user interaction.

---

## Phase 4 — Auto-update and polish

**Status:** Not started

- [ ] GitHub release-based auto-updater.
- [ ] Visual update progress (check → download → install → reload),
      mirroring the pattern used by Panel de Control.
- [ ] Honest compatibility table per device in the README.
- [ ] Final visual identity for the suite.

**Exit criterion:** a new tagged release on GitHub is offered to
existing installs through the plugin UI and installs cleanly.

---

## Phase 5 — Native daemon  *(Conditional)*

**Status:** Not started

Only if Phase 0 confirms that the Python backend cannot sustain the
latency or resolution needed for the more advanced Haptic Studio
features (synthetic patterns, real-time envelope shaping).
