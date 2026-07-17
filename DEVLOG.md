# Dev Log

A chronological log of technical decisions and progress. Newest entries
appear at the top.

The intent of this file is to be the source of truth for "why is the
code like this" — every non-trivial decision should be findable here.

---

## 2026-07-17 — Phase 0 close: rumble sweep results

A rumble sweep was driven through D-Bus at intensities
`0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 0.7, 1.0` (1s each, 0.5s gap), then
stopped. Outcome:

- All values produced a perceptible, **gradual** response. No abrupt
  on/off threshold was reported at the low end, and no obvious
  saturation knee at the high end.
- This contradicts the SDD's working assumption that handheld rumble
  motors typically show a hard dead-zone at the bottom and early
  saturation at the top. On the Legion Go S the motor is more
  obedient than the SDD assumed.

**Implications for Haptic Studio**

- The default response curve can start **linear** — no aggressive
  dead-zone compensation is required.
- The ceiling for what Haptic Studio can do on this device is higher
  than the SDD expected. Fine intensity adjustments will translate to
  a real perceptual difference; we are not limited to gain +
  envelope shaping alone.
- The remaining calibration (subjective "punch" shaping, exact curve
  preference) is **deferred into Haptic Studio itself**, where the
  user will have a live intensity slider and curve editor. The
  initial `DeviceProfile` for the Legion Go S will ship conservative
  defaults: `gain = 1.0`, linear curve, no dead-zone, no saturation
  cap.

**Phase 0 status**

| Phase 0 item | Result |
| --- | --- |
| Kernel + driver (`hid_lenovo_go_s`) | Confirmed — ships with SteamOS 3.8.23 |
| Gamepad topology (hidraw/event nodes) | Confirmed — gamepad is `hidraw5` / `event2`, owned by InputPlumber |
| Steam Input mediation | Partially answered — Steam only sees the virtual `deck-uhid` gamepad; out of scope for MVP |
| Motor profiling | Confirmed gradual response; fine calibration deferred into Haptic Studio |

Phase 0 is **closed**. Haptic backend path is locked to InputPlumber
D-Bus `org.shadowblip.Output.ForceFeedback.Rumble(double)` on
`CompositeDevice0`.

---

## 2026-07-17 — Phase 0 hardware validation: findings

Validation ran on a real Lenovo Legion Go S over SSH. Probe scripts
`scripts/probe{,2,3}.sh` capture the raw evidence; archived under
`docs/phase0/`.

**Setup**

- SteamOS 3.8.23 (BUILD 20260715.2), kernel
  `6.16.12-drmexec7-valve24.5-1-neptune-616-drm-exec-gf253f5da553e`
  (Valve neptune base — same codebase as the Steam Deck).
- `VARIANT_ID=steamdeck` in `/etc/os-release`: Valve ships the Go S
  SteamOS as a `steamdeck` variant overlay, not a separate codename.

**Items confirmed**

1. **Kernel + driver.** `hid_lenovo_go_s` ships with this SteamOS
   kernel — already loaded at boot, no need for a 7.x kernel. Two
   modules present on disk: `hid-lenovo-go.ko` (original Legion Go)
   and `hid-lenovo-go-s.ko` (Go S). Author: Derek J. Clark, GPL.
   The SDD assumption that this driver was pending mainline in
   Linux 7.1+ is outdated: it is already backported here.
2. **Gamepad topology.** The internal MCU presents as a compound USB
   device `1a86:e310` (QinHeng bridge) with **6 HID interfaces**,
   each backed by one hidraw device. InputPlumber maps them by
   `interface_num` (see `/usr/share/inputplumber/devices/50-legion_go_s.yaml`):
   - iface 2 → `/dev/hidraw1` (mouse + touchpad, blocked)
   - iface 5 → `/dev/hidraw4` (IMU)
   - iface 6 → `/dev/hidraw5` (**gamepad** — buttons, sticks, triggers)
   - iface 0/3/4 → also bound by `hid-lenovo-go-s` (auxiliary)
   The gamepad is also exposed as `/dev/input/event2` (joystick
   `js0`, name `"Legion Go S"`) with FF capabilities
   (`B: FF=107030000`).
3. **InputPlumber composite device.** InputPlumber is the input
   manager on this SteamOS build. It captures the native gamepad and
   re-emits a **virtual Steam Deck gamepad** ("Valve Steam Deck
   Controller") via `deck-uhid`, surfaced as `/dev/input/event18`
   (`"Microsoft X-Box 360 pad 0"`, vendor `28de`). Steam and games
   see only the virtual device.
4. **D-Bus rumble API.** The composite device at
   `/org/shadowblip/InputPlumber/CompositeDevice0` exposes the
   `org.shadowblip.Output.ForceFeedback` interface:
   - `Rumble(double value)` — set rumble intensity, 0.0–1.0.
   - `Stop()` — stop rumble.
   - `Enabled` (readwrite bool, default true).
   `OutputCapabilities` confirms `ForceFeedback`,
   `ForceFeedbackUpload`, `ForceFeedbackErase` are supported. This
   is the clean integration point for Haptic Studio.

**Items partially confirmed**

5. **Steam Input mediation.** Not directly tested. The gamepad the
   games see is the virtual `deck-uhid` device, so Steam Input
   applies its own processing on top of that. Intercepting rumble
   between Steam and the kernel would require going below
   InputPlumber — out of scope for the MVP.

**Items still open**

6. **Motor profiling.** Dead-zone, saturation point and latency still
   need to be measured by driving `Rumble(d)` with a sweep of values
   and observing the physical response. This requires a write test,
   pending explicit user confirmation (the only Phase 0 step that is
   not read-only).

**Architectural decision**

For Haptic Studio on the Legion Go S, the **primary rumble path is
the InputPlumber D-Bus `ForceFeedback.Rumble(double)` method on
`CompositeDevice0`**.

- It is the officially supported integration surface.
- It avoids conflicts with InputPlumber's exclusive ownership of
  `/dev/hidraw5` and `/dev/input/event2`.
- The `d` argument is already a 0.0–1.0 float — gain is essentially
  free.
- It supports per-effect upload/erase for advanced patterns later.

Going below InputPlumber (writing to `hidraw5` directly) would break
its input translation. Going above InputPlumber (intercepting Steam
Input output) is not feasible from a Decky plugin. D-Bus is the
sweet spot.

What D-Bus does **not** give us directly is per-event gain on rumble
coming from games — `Rumble()` is fire-and-feel, not a transform on
the FF stream. Global gain as "set baseline intensity" works;
"amplify whatever the game sends" is not exposed and would need
either the CompositeDevice's `InterceptMode` /
`SetInterceptActivation` methods (worth investigating in Phase 2)
or a path below the kernel. Filed as Phase 2 stretch.

---

## 2026-07-17 — Repository, build pipeline, first release

**Done**

- Created `scripts/package.sh` — a small bash script that bundles the
  plugin into the zip layout Decky Loader expects (top-level directory
  named after the plugin, with `dist/`, `package.json`, `plugin.json`,
  `main.py`, `defaults/`, `py_modules/`, `LICENSE`, `README`). Source
  maps are excluded to keep the artifact small. The script reads name
  and version from `package.json` so it stays correct as we tag
  releases. It will be reused by the release GitHub Action later.
- Bootstrapped the toolchain on the dev machine:
  - `pnpm 11.13.1` installed via `npm i -g pnpm` (corepack not
    available on this image).
  - `pnpm install` brings in `@decky/ui 4.12.0`, `@decky/api 1.1.3`,
    `@decky/rollup 1.0.2`, `react-icons`, `rollup`, `typescript`.
    No `docker` (no decky CLI) — handled by the manual packaging
    script instead.
- `pnpm run build` produces `dist/index.js` (~7 KB) plus a sourcemap.
- Packaged `out/decksense-v0.0.1.zip` (21 entries, ~25 KB).
- Created the GitHub repository at `Heric-Olier/decksense` as
  **private** until the MVP is ready, and pushed `main`.
- Tagged `v0.0.1` and published the first GitHub Release with the zip
  as a release asset.

**Notes**

- pnpm 11 warns that the `pnpm.peerDependencyRules` field in
  `package.json` is no longer read. The install and build still work,
  so the field can be removed (or migrated to `.npmrc`) in a follow-up
  cleanup commit.
- The release is only reachable from a GitHub account that has access
  to the private repo. Installing from the device needs either a
  public repo or a GitHub token configured in Decky Loader. This is
  expected for the "private until MVP" decision and will revisit when
  Display Studio lands.

**Next**

- Decide install path on the Lenovo Legion Go S (make the repo public
  for this skeleton, or pass the zip manually).
- Phase 0 — hardware validation. First task: confirm the SteamOS
  kernel version on the device and whether the rumble path goes
  through the mainline `hid-lenovo-go-s` driver or through
  InputPlumber.

---

## 2026-07-17 — Bootstrap

**Decisions**

- **License: GPL-3.0.** Coherent with the Decky Loader ecosystem
  (GPL-2.0) and protects downstream contributions.
- **No native daemon at launch.** Backend access to hardware lives
  entirely in the Python backend, talking to sysfs / hidraw /
  InputPlumber. A native daemon is deferred to Phase 5 and only if
  latency / resolution requirements demand it. This matches the
  architecture used by other ecosystem plugins and keeps the build
  surface small.
- **Plugin runs with the `_root` flag.** Hardware access (sysfs,
  hidraw) requires elevated privileges. The flag is declared in
  `plugin.json` so the user knows up front what the plugin needs.
- **Module layout under `py_modules/decksense/`** with one subpackage
  per module (`display`, `haptic`, `profiles`, `updater`). Each
  subpackage will own its own `adapters`, `services` and `domain`
  types. This keeps module boundaries explicit so each module can grow
  independently and so tests can mock at the adapter boundary.
- **Layered backend.** Conventions within each module:
  - `adapters/` — hardware I/O (the only place that touches sysfs /
    hidraw / subprocesses).
  - `services/` — business logic, agnostic of the hardware path.
  - `domain.py` — pure data models (Pydantic once dependencies land).
  The `main.py` entrypoint exposes thin RPC methods that delegate to
  services. This lets us swap the kernel-sysfs path for InputPlumber
  without touching business logic, and mock hardware in tests.
- **Conventional Commits** as the commit message convention
  (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`).
- **Repository language: English** for code, docs and commits, so the
  plugin is approachable for the wider Decky community.

**Done**

- Initialized the repository with the structure of the official
  `decky-plugin-template` as a base.
- Skeleton `plugin.json`, `package.json`, `rollup.config.js`,
  `tsconfig.json`, `main.py`, plus empty module subpackages.
- Frontend skeleton (`src/index.tsx`) with three empty panel sections
  for Display Studio, Haptic Studio and Game Profiles.
- Initial settings schema in `defaults/settings.json`.
- `README.md`, `ROADMAP.md` and this file as the public tracking
  surface.

**Next**

- Phase 0 — hardware validation on the Lenovo Legion Go S. First task:
  confirm the SteamOS kernel version and whether the Legion Go S
  rumble path goes through the mainline `hid-lenovo-go-s` driver or
  through InputPlumber.
