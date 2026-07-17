# Roadmap

Phases follow the internal Software Design Document, but **execution
order has been adjusted** after Phase 0:

1. **Phase 4 (auto-update) is pulled forward** to enable the
   "commit → push → update on device" cycle before any feature work.
2. **Phase 1 (Display) and Phase 2 (Haptic) run as a parallel lab** in
   small increments (one or two new controls per release), not
   sequentially.
3. **UX/UI is a cross-cutting concern** in every increment: tabbed
   navigation with L1/R1 (SteamOS shoulders), status indicators,
   live-preview sliders, bento cards for presets, marquee text where
   Steam Deck QAM would otherwise truncate.

Statuses: `Not started` · `In progress` · `Blocked` · `Done`.

---

## Phase 0 — Hardware validation  *(Blocking)*

**Status:** Done

- [x] SteamOS kernel + `hid_lenovo_go_s` driver — already in SteamOS
      3.8.23 (kernel 6.16.12 neptune).
- [x] Gamepad topology + rumble path — InputPlumber D-Bus
      `org.shadowblip.Output.ForceFeedback.Rumble(double)` at
      `/org/shadowblip/InputPlumber/CompositeDevice0`.
- [x] Steam Input mediation — Steam sees only the virtual `deck-uhid`
      gamepad; out of scope for MVP.
- [x] Motor profiling — gradual response across 0.05–1.0, no obvious
      dead-zone or saturation knee.

---

## Phase 4 — Auto-update and core UX shell  *(Current focus)*

**Status:** In progress

Infrastructure needed before feature work pays off. Pulls forward from
its original slot.

- [ ] CI workflow — build + typecheck on every push and PR.
- [ ] Release workflow — on `v*` tag, build + package + upload the zip
      to the GitHub release automatically.
- [ ] Dependabot — npm and github-actions, weekly, conservative.
- [ ] Tabbed navigation shell — `SectionDef` registry as single source
      of truth, `TabBar` with `Focusable`, L1/R1 (shoulder buttons) to
      cycle tabs via `SteamClient.Input.RegisterForControllerInputMessages`.
- [ ] `MarqueeText` and `AlertDot` utility components.
- [ ] Backend `self_updater` — `check()`, `install()`, `restart_loader()`
      following the Panel de Control pattern (never raises; status dict;
      `LD_LIBRARY_PATH` stripped when calling systemctl).
- [ ] Frontend `useUpdate` hook + `UpdatePanel` + `UpdateModal` with
      coarse progress states.
- [ ] Honest compatibility table per device in the README.

**Exit criterion:** a new tagged release is offered to existing
installs through the plugin UI and installs cleanly. Tab navigation
with L1/R1 works. Deployed as `v0.0.2`.

---

## Phase 1 — Display Studio  *(Lab, parallel with Phase 2)*

**Status:** Not started — incremental from `v0.0.3`

Built one or two controls at a time, deployed often.

- [ ] Gamescope adapter (subprocess wrapper for saturation, contrast,
      sharpness, gamma, color temperature).
- [ ] **Preset 1: Sharp** — realce de nitidez + contraste.
- [ ] **Preset 2: OLED-like** — gamma + saturación compensando paneles
      LCD.
- [ ] Confirmation timer (auto-revert after N seconds if not
      confirmed).
- [ ] Bento-card preset picker with mini-preview.
- [ ] *Later:* Pixel Art, per-game profiles.

**Exit criterion for `v0.0.3`:** Sharp and OLED-like presets apply and
revert cleanly through the QAM, with the confirmation timer enforced.

---

## Phase 2 — Haptic Studio  *(Lab, parallel with Phase 1)*

**Status:** Not started — incremental from `v0.0.3`

Built one or two controls at a time, deployed often. Backend path is
locked from Phase 0: InputPlumber D-Bus `Rumble(double)`.

- [ ] Haptic backend abstraction (`HapticBackend` interface).
- [ ] Legion Go S implementation (D-Bus client to InputPlumber
      `CompositeDevice0`).
- [ ] **Gain slider** with live preview (the slider drag emits
      `Rumble(value)` so you feel it in real time).
- [ ] `DeviceProfile` for the Legion Go S with conservative defaults
      (gain 1.0, linear curve).
- [ ] *Later:* response curve editor, "punch" envelope, per-motor
      calibrations.

**Exit criterion for `v0.0.3`:** the gain slider visibly and audibly
drives the rumble motor, with the value persisted and reapplied on
plugin reload.

---

## Phase 3 — Game Profiles

**Status:** Not started

- [ ] AppId detection.
- [ ] Preset application on game change (Display + Haptic combined).
- [ ] Profile management UI (list, edit, duplicate, delete).

**Exit criterion:** launching a game with a stored profile applies the
expected Display and Haptic settings without user interaction.

---

## Phase 5 — Native daemon  *(Conditional)*

**Status:** Not started

Only if a Python backend cannot sustain the latency or resolution
needed for advanced Haptic Studio features (synthetic patterns,
real-time envelope shaping). Phase 0 confirmed gradual motor response,
so this is unlikely to be needed.
