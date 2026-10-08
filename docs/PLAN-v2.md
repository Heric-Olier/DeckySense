# DeckySense — Plan v2 (retomada, oct-2026)

> Base: `docs/INVESTIGACION-2026-10.md` + los 4 informes crudos. Principios:
> **alcance honesto** (no fingir lo que el hardware/stack no permite), **fases
> cortas con resultado visible cada una** (el dueño quiere ver avances seguidos),
> **UX de nivel Panel de Control** desde el día uno, arquitectura por capas ya
> existente (adapters/services/domain) sin daemon nativo (condición: P2).

---

## Estrategia en 4 vías

### Vía 1 — Exprimir el motor real (sin depender de nadie)
Lo que SÍ se puede hoy, en orden de impacto:
1. **Nivel de firmware "strong"** (combo Legion L + D-pad) → el plugin lo hace
   descubrible: tarjeta guía con el combo + cómo verificarlo + persistencia (Legion Space/Windows).
2. **Cap/atenuación** (si P1 ✓) → slider 0–100% que SÍ afecta al rumble de juego (via EVIOCSGAIN en event2, re-aplicado en loop).
3. **On/off de FF** (`Enabled` D-Bus) → toggle por juego + workaround del bug #706.
4. **Preview/test por motor + balance** (ya existe v0.0.43; pulir).
5. Motores ruidosos: guía para bajar nivel (la queja inversa también está documentada).

### Vía 2 — Efectos sintéticos para carreras (pionero, experimental)
Si P2 ✓: un módulo "Race Haptics" que lee telemetría (PCSX2 PINE para GT4 en la Legion;
otros juegos después) y sintetiza efectos (RPM, pianos, derrape, ABS) hacia los motores.
Sin precedente público — es nuestra ventana para hacer algo único, con etiqueta EXPERIMENTAL
y validación sensorial con el dueño. Si P2 ✗: se replantea (D-Bus Rumble con patrones como plan B limita a pulsos, sin mezcla con el juego).

### Vía 3 — Upstream (donde vive la mejora "de verdad")
- **PR #729** (routing haptics Go S + haptic pulses + DS5 v2): seguimiento activo; cuando mergee, re-verificar y aprovechar los reportes nuevos.
- **PR #489** (`Scale`): comentar/empujar para que incluya **escala >1.0** (o proponer variante). Si el maintainer acepta, DeckySense lo expone como "Boost" por juego.
- **Kernel Go S**: proponer a Derek J. Clark (LKML/InputPlumber) atributos de rumble para `hid-lenovo-go-s` como los del Go/Go2 (`rumble_intensity`, `rumble_mode`). Evidencia de demanda: el propio LeGo-Vibe-Control dice "Go S not supported".
- **Valve #10129** (slider de rumble por juego en SteamOS): soplar el caso Go S.

### Vía 4 — Infra robusta (mata el dolor de la v0.0.4x)
Portar el patrón Panel de Control: self_updater completo (lock, notas multi-versión,
permisos de zip, SSL bundle, contrato de error), `deploy-to-device.sh` para iterar rápido,
journal jsonl, SettingsStore atómico, reporter básico con PII redactada. Resultado: ciclo
"commit → update en la consola" sin fricción — el problema que enterró la primera intentona.

---

## Fases (cortas, con resultado visible)

| Fase | Entrega | Criterio de salida |
|---|---|---|
| **F0-bis · Pruebas** | P1–P5 en la Legion (sensoriales con el dueño) | Veredicto por prueba: vía habilitada o descartada; informe corto |
| **F1 · Haptic Studio v2** | Panel Motor: guía firmware, cap slider (si P1), toggle FF, preview+balance, aviso #706; UX base (focus styles, chips, marquee) | Se siente/funciona en la consola; deploy vía updater nuevo |
| **F2 · Infra** | Updater PdC-style + deploy script + journal + settings atómicos | Update in-app sin dolor; logs útiles para diagnóstico |
| **F3 · Game Profiles** | Detección de appid + aplicar preset (haptic cap/FF + display) por juego | Perfil aplicado al lanzar un juego real |
| **F4 · Display Studio** | gamescope: Sharp / OLED-like + auto-revert 15s | Presets aplican y revierten limpios |
| **F5 · Race Haptics (pionero)** | Telemetría → efectos sintéticos a motores (si P2 ✓); + gestión upstream (PRs/kernel) | Demo sensible: GT4 con "pianos/RPM" en la Legion |

Nota de orden: F1 primero (es el deseo declarado); F4 puede intercalarse cuando se quiera
algo vistoso de bajo riesgo. F5 es experimental — se etiqueta como tal en la UI.

## Arquitectura (delta sobre la actual)

- Mantener `py_modules/deckysense/{haptic,display,profiles,updater}` + adapter/service/domain.
- `haptic/adapters`: añadir `EvdevGainAdapter` (P1) y `SteamPadInjector` (P2, experimental).
- El "cap" del slider = `EVIOCSGAIN` en event2 **re-aplicado** (InputPlumber resetea a full);
  vigilar también `Enabled` y `SetTargetDevices` para no pisarlo.
- Sin daemon nativo por ahora; si F5 lo exige (latencia), decisión explícita y documentada.

## Riesgos

- El stack cambia entre versiones de SteamOS (regresión real: Ally X 3.8.16→3.9.x): cada update grande → re-correr P1–P5 (runbook en skill `deckysense`).
- PRs upstream pueden no mergear: Vía 1 no depende de ellos; Vía 3 es upside.
- P2 puede fallar (Steam podría no re-emitir FF de terceros): F5 queda condicionada.
- Escribir a event2/HID compite con InputPlumber: todo cambio con verificación y revert.

## Referencias

- Investigación: `docs/INVESTIGACION-2026-10.md` · crudos: `docs/research/2026-10-07/`.
- PRs: ShadowBlip/InputPlumber #489 y #729. Issue Valve: steam-for-linux #10129.
  Issues InputPlumber: #704, #706, #709.
- Referencia UX/infra: Hooandee/panel-de-control (informe-3).
