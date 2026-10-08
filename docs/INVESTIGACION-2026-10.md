# DeckySense — Investigación consolidada (7-oct-2026)

> Retomada del proyecto tras 2.5 meses. Esta es la síntesis ejecutiva de la
> investigación a fondo (4 informes crudos en `docs/research/2026-10-07/`),
> con verificación EN VIVO sobre la Legion Go S (SSH).
> **Conclusión corta: el "amplificar el haptic de los juegos" hoy tiene una
> pared arquitectónica real en SteamOS — pero hay un boost firmware que casi
> nadie conoce, dos PRs upstream cerca de abrir la puerta, y una vía pionera
> para juegos de carreras que vale explorar.**

---

## 1. Estado del sistema (verificado hoy por SSH)

- SteamOS 3.9.2 (build 20260925.101) · kernel `7.2.7-valve1-1-neptune-72`.
- InputPlumber **0.78.0** (target activo: `deck-uhid` = "Valve Steam Deck Controller"; también existe `dbus0`).
- Plugin `deckysense` **v0.0.43** instalado en `~/homebrew/plugins/` (flags `root`, `_root`).
- Drivers HID cargados: `hid-lenovo-go-s` (Go S, de Derek J. Clark) + `playstation`.
- El driver `hid-lenovo-go-s` expone: `gamepad/` (poll_rate, dpad_mode, auto_sleep, mode), `imu/`, `mouse/`, `touchpad/`, `mcu_id`, `os_mode`, `leds/go_s:rgb:joystick_rings`. **CERO atributos de rumble/vibración.**

## 2. La cadena de force feedback real (corregida vs. fase 0)

```
Juego → pad virtual de Steam (uinput 28de:11ff, "Microsoft X-Box 360 pad 0", event18)
      → Steam Input → deck-uhid [feature report 0xEB "ID_TRIGGER_RUMBLE_CMD" por hidraw7]
      → InputPlumber (procesa SET_REPORT, PackedRumbleReport)
      → escribe efecto FF a /dev/input/event2 (gamepad físico 1a86:e310, con EVIOCGRAB)
      → kernel: driver XPAD (XTYPE_XBOX360) + ff-memless → paquete USB al MCU → motores
```

- **Corrección a fase 0:** los juegos NO ven el deck-uhid; ven el **pad virtual de Steam** (28de:11ff). El deck-uhid lo consume Steam.
- El gamepad físico lo maneja **xpad** (¡no un driver Lenovo dedicado!) con FF vía `ff-memless`.
- InputPlumber tiene un camino hidraw alternativo para el rumble (`src/drivers/legos/xinput_driver.rs`, report 0x04) que **no está cableado** — lo arregla el PR #729.
- `xpad + ff-memless` **sí aplica gain** (`strong*gain/0xffff`) al reproducir en el físico. El EVIOCGRAB de InputPlumber impide "events" de terceros, pero `EVIOCSGAIN` es un ioctl de device (no un inject event) → **pendiente prueba empírica P1**.

## 3. Qué expone cada capa (verificado)

| Capa | ¿Amplificar? | ¿Atenuar? | Notas |
|---|---|---|---|
| Firmware MCU (Go S) | **SÍ: 4 niveles** (off/low/medium/**strong**) | sí | Combo **Legion L + D-pad Arriba/Abajo** (vibra 2s). Default: medium. Fijable en Legion Space (Windows) y persiste. |
| Kernel `hid-lenovo-go-s` | no | no | Sin atributos de rumble (0 menciones en el código, verificado también en la consola). |
| Kernel `hid-lenovo-go` (Go/Go2) | no (niveles) | sí | `rumble_intensity` (off/low/medium/high), `left/right_handle/rumble_mode` (**fps/racing/standard/spg/rpg**), `rumble_notification`, `touchpad/vibration_*`. Mergeado en Linux 7.1. **No aplica al Go S.** |
| InputPlumber D-Bus | no | parcial | `org.shadowblip.Output.ForceFeedback`: `Rumble(double 0..1)`, `Stop()`, `Enabled` (bool rw). No existe Rumble2. `InterceptMode` es de ENTRADA, no FF. |
| InputPlumber PR #489 (open) | — | sí (Scale 0..1) | Property `Scale` pendiente de merge/diseño. **La vía upstream para gain de juego.** |
| InputPlumber PR #729 (open) | — | — | Fix de routing: añade OutputCapabilities a las sources (`legos_xinput`), reenvía haptic pulses del Steam Deck, DS5 emulation v2. Clave para Go S. |
| Steam | no | sí | Toggles "Game Rumble"/"Steam Haptics"; sin slider por juego (FR Valve #10129, abierta desde 2023). |
| FF_GAIN (kernel) | **no** (techo 100%) | sí | Vía "rog-ally-rumble-fixer" (re-aplicar en loop porque InputPlumber resetea): probado en Ally; reportado OK en Legion Go 1. **Pendiente P1 en Go S** (sobre event2). |

## 4. El hallazgo firmware (lo mejor de esta investigación)

Manual oficial Lenovo + usuarios: la intensidad del mando integrado tiene 4 niveles de fábrica
(**off / low / medium / strong**, default **medium**) y se cambia con **Legion L + D-pad Arriba/Abajo**.
Subir a strong es, HOY, el único "amplificar" real disponible. También denunciado: la queja inversa
(motores ruidosos / "más fuerte que el volumen del juego") — o sea un **cap** también tiene valor real.
Runbook de recuperación si el rumble desaparece: re-flashear firmware del mando (v0.38) con `fwupdmgr`.

## 5. Upstream vivo (a empujar)

- **ShadowBlip/InputPlumber PR #729** — "fix: Various Rumble and Gamepad Issues" (pastaq): routing de
  rumble/haptics en Go S + `TriggerHapticPulse` del deck-uhid + DS5 v2. **Pendiente de merge.**
- **ShadowBlip/InputPlumber PR #489** (ShadowApex): property `Scale` 0..1 en ForceFeedback. Estancado
  en discusión de diseño. Extenderlo (>1.0 y/o por-source) sería EL gain de juego.
- Issues a seguir: #704 (freeze 1s por retry de FF upload), #706 (rumble duplicado con mando externo
  en Go S; workaround `busctl … Enabled false`), #709 (deck-uhid roto en Bazzite).
- **Kernel:** serie v6 de Derek J. Clark mergeada para Linux 7.1 (Go/Go2); el driver del Go S sigue sin
  rumble. El autor anunció "later patch series" para mover funciones hoy en userspace (InputPlumber) al kernel.

## 6. Comunidad y proyectos hermanos

- `Rayekkk/LeGo-Vibe-Control` (Go/Go2, sysfs): *"Legion Go S is not supported — its hid-lenovo-go-s
  driver does not expose vibration control via sysfs"*.
- `alicerum/rog-ally-rumble-fixer` (FF_GAIN loop vía evdev; Ally X + reporte OK en Go 1).
- `piyush-tyagi-13/ally-vibe-control` (Ally X, sysfs `vibration_intensity`).
- HHD (Bazzite): su instalador **bloquea SteamOS** ("not canon"); en kernels 7.1+ choca con
  `hid-lenovo-go-s` (hhd#332); tampoco tiene slider de intensidad para Legion (issues #206/#301).
  **Cambiar de stack NO resuelve.**
- PCSX2/GT4: rumble por SDL estándar; sin slider; bugs históricos (solo LargeMotor en Deck). El rumble
  del juego funciona через la cadena normal en Go S. Rumble por telemetría a motores internos:
  **sin precedente público** (SimHub lo rechazó explícitamente; DSX es Windows+DualSense externo).

## 7. Técnicas de Panel de Control (Hooandee) a adoptar

Ver informe crudo (informe-3). Destacados: updater completo (lock, multi-version notes, permisos de
zip, SSL bundle, contrato de error `{ok, needs_restart, message}`), focus styles con box-shadow para
CEF, `QamPanelGate` (anti-bug #855), `valueToast` con `eType:17` sin sonido, ConfirmDialog con
auto-revert (15s), journal jsonl con coalescing, reporter con código PDC-XXXX y redacción de PII,
SettingsStore con merge + escrituras atómicas, `user_session.spawn_args()` (root→usuario sin
runuser), CI con release-please + guard + provenance. Ritmo del repo: ~120 releases en 3.5 meses.

## 8. Preguntas empíricas abiertas (próximas pruebas, en la consola del dueño)

- **P1** — ¿`EVIOCSGAIN` sobre `/dev/input/event2` modula en vivo el rumble (D-Bus `Rumble` y de juego)?
  Si ✓ → slider real 0–100% para juegos (con firmware en strong como techo). Alta probabilidad por evidencia Ally/Go1.
- **P2** — ¿Un tercero puede subir/reproducir un efecto FF sintético al **pad virtual de Steam**
  (uinput 28de:11ff) y que Steam lo re-emita al mando? Si ✓ → efectos por telemetría (GT4/PINE:
  pianos, RPM) hacia los motores internos = la vía "carreras".
- **P3** — ¿`Enabled=false` (D-Bus) silencia el FF de juegos? (toggle + workaround #706).
- **P4** — Comparar sensación/curva con firmware en medium vs strong (para calibrar el futuro slider).
- **P5** — Re-validar `Rumble(double)` D-Bus y preview del plugin v0.0.43 sobre InputPlumber 0.78.

## 9. Anexos

- `docs/research/2026-10-07/informe-1-inputplumber-ff-pipeline.md` — flujo FF + API D-Bus + PRs (código real v0.81).
- `docs/research/2026-10-07/informe-2-kernel-driver.md` — hid-lenovo-go(-s), LKML, mainline 7.1, comandos de verificación.
- `docs/research/2026-10-07/informe-3-panel-de-control-tecnicas.md` — 22 técnicas replicables + qué copiar.
- `docs/research/2026-10-07/informe-4-comunidad-y-proyectos.md` — hilos, plugins hermanos, HHD, veredicto comunitario.
