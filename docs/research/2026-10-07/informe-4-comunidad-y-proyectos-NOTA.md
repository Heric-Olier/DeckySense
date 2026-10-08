# Informe de comunidad — NOTA (informe-4)

> El informe completo (~15 KB, con URLs y citas) fue producido por el subagente de investigación
> comunitaria el 7-oct-2026 y se entregó dentro de la sesión de trabajo; sus hallazgos quedaron
> **consolidados** en `docs/INVESTIGACION-2026-10.md` (§4 firmware, §6 comunidad, §7 carreras).
> No se preservó como archivo independiente (los logs de subagentes truncan líneas largas).
> Para recuperar el texto completo: `session_search` sobre la sesión del 2026-10-07 ("DeckySense").

## Hallazgos clave (con fuentes)

- **BOOST FIRMWARE (el hallazgo principal)**: 4 niveles en el mando — off / low / medium / **strong**
  (default: medium). Combo: **Legion L + D-pad Arriba/Abajo** (vibra 2 s al cambiar).
  Manual oficial: `download.lenovo.com/consumer/mobiles_pub/lenovo_legion_go_s_ug_en.pdf` (Controller vibration).
  También fijable desde **Legion Space (Windows)** — persiste en el MCU al volver a SteamOS.
- Rumores/quejas en r/LegionGo: "una sola etapa" de rumble, feel ~3/10 vs DualSense 10/10 (hilo `1pbw21s`);
  quejas de exceso/ruido (`1m5h52q`, `1r50my8`); recuperación si el rumble desaparece = re-flash de firmware
  del mando (v0.38) con `fwupdmgr` (`1mmmnvt`).
- Plugins hermanos (ninguno soporta Go S):
  - `Rayekkk/LeGo-Vibe-Control` (Go/Go2; sysfs; *"Legion Go S is not supported"*).
  - `alicerum/rog-ally-rumble-fixer` (FF_GAIN en loop; probado OK en Legion Go 1).
  - `piyush-tyagi-13/ally-vibe-control` (Ally X, sysfs `vibration_intensity`).
  - `dawidmpunkt/RumbleDeck` (mod de HARDWARE para Steam Deck).
- **HHD**: instalador bloquea SteamOS ("not canon"); conflicto con `hid-lenovo-go-s` en kernels 7.1+
  (`hhd-dev/hhd#332`); sin slider de intensidad para Legion (`#206`/`#301`). No es vía.
- **InputPlumber**: PR `#729` (routing haptics Go S) y PR `#489` (scale D-Bus); issues `#706`, `#704`, `#709`.
- **Valve**: slider de rumble por juego — `ValveSoftware/steam-for-linux#10129` (abierta desde 2023).
- **PCSX2**: rumble por SDL estándar, sin slider; bug histórico "solo LargeMotor" en Steam Deck.
- **SimHub**: no soporta salida a motores de gamepad (respuesta oficial del autor); telemetría→motores
  internos = terreno sin precedente público (nuestra posible ventana P2).
- **Veredicto**: hoy lo único que "amplifica" es el firmware (combo); el resto = reducir/capar (FF_GAIN),
  esperar upstream (#729/#489) o vías pioneras (P2).
