# Informe 2 — Ecosistema háptics/telemetría + ajuste Steam (2026-10-08)

Investigación delegada (subagente 2, deleg_64c84333). Conclusiones clave:

- **Telemetry-to-haptics para PS2 no existe públicamente** → terreno virgen.
- **SimHub NO puede enviar a gamepads** (solo serie/audio) → descartado como puente.
- **El "Rumble Intensity" de Steam es del Steam Controller (2026)**, no de mandos
  genéricos como el interno del Go S → descartado para nosotros.
- **PCSX2 SÍ tiene escala de vibración por motor 0–200%** (Large/Small Motor
  Vibration Scale) → amplificación real para juegos PS2. Verificado en la config
  de la consola (PCSX2.ini: LargeMotorScale=1.0, SmallMotorScale=1.0, PCSX2 v2.9.102).
- Amplificar >100% en el resto del stack: imposible hoy (kernel/D-Bus/Steam);
  puertas: firmware del mando (no disponible en Go S SteamOS) y PR #489 upstream.

```json
{
  "proyectos_emuladores_haptics": "NO existe ningún proyecto público que conecte emuladores de PS2 (PCSX2) —ni RetroArch/Dolphin— a rumble custom o 'HD haptics' derivado de TELEMETRÍA; en emuladores el rumble es siempre game-driven (el juego emulado ordena los motores vía el DualShock 2 emulado). Verificado con búsquedas en GitHub/foros/Reddit (oct-2026).\n• PCSX2: rumble por SDL haptic estándar y SÍ tiene escala por motor (Settings > Controllers > Port 1 > Settings): 'Large Motor Vibration Scale' y 'Small Motor Vibration Scale' — float 0.00–2.00 (0–200%), default 1.00: ATENÚA Y AMPLIFICA dentro del emulador (verificado en código: pcsx2/SIO/Pad/PadDualshock2.cpp, descripción 'Increases or decreases the intensity...'; issue #9622 usa 'even putting strength at 200%'). Bugs conocidos: en Steam Deck a veces solo llega LargeMotor; adaptadores PS2→USB sin rumble (#14929); 'DualSense Enhanced Mode' solo LED+vibración.\n• GT4: hilos GTPlanet/Reddit sobre vibración constante (bajan Small Motor a ~4%) y petición de reducirla en Spec II — todo game-driven, sin telemetría.\n• RetroArch: Settings > Input > Haptic Feedback/Vibration > Vibration Strength = 0–100% en pasos de 5% (solo atenúa) y con bugs de que se ignora (EmuELEC #975; RetroArch #16896). Rumble vía driver 'udev'.\n• Dolphin: rumble SDL con bind 'Motor L'/'Motor R'; SIN ajuste de intensidad (foro Dolphin: no se puede ajustar la fuerza, solo mapearla). Steam Input añadió soporte 'GameCube rumble' con adaptador en modo PC (beta 4-jun-2026).\n• Proyectos adyacentes (no PS2, casi todos Windows): tocaedit/xboxshakeit (SimHub→4 motores de mando Xbox), AlteredAJ/dualsense-haptics y shiftedx/dualsense-command (telemetría racing→DualSense), elenhinan/ESPTurismo (telemetría GT7→motores ESP32), Intiface Game Haptics Router (reruteo de rumble), ARMSX2 #241 (haptics en emulador PS2 Android), bHaptics (chalecos).\n• Implicación DeckySense: telemetry-to-haptics para PS2 = terreno virgen; nuestro bridge GT4→SimHub solo alimenta shakers/dashboards (SimHub no toca motores del mando) y la vía P2 (inyectar FF al pad virtual de Steam) sería pionera.",
  "simhub_gamepads": "SimHub NO envía efectos a los motores de un gamepad. Respuesta oficial del autor (Wotever, 25-ago-2020) en el hilo 'Control rumble motors via gamecontroller': 'No it's not implemented... sending vibrations requires the exclusive access to the controller and it would mess up with some games'.\n• Wiki 'ShakeIt V3 Motors — Output Configuration' (vigente): salidas soportadas = fans/motores de vibración vía Arduino (motor shield/monster moto/PWM, hasta 12 canales), Gametrix, Forcefeel y motores de pedales Fanatec (solo USB); ajustes por dispositivo: Threshold (0–100) y Minimum force; NO lista gamepads.\n• 2026: SimHub amplió a pedal reactors nativos (Simagic/Fanatec/VNM) y añadió 'fan and haptic motor support to the Standard Serial protocol' + 'Standard HID protocol' (device authoring) — siguen siendo dispositivos propios/custom, no los motores internos de un mando.\n• Único puente comunitario a un mando: tocaedit/xboxshakeit = emulador de 'SimHub ShakeIt Device' que vía par de puertos COM virtuales (com0com) mapea los 4 motores de un mando Xbox Series X/S a efectos de telemetría. Windows-only (com0com es driver de kernel) → no viable en SteamOS/wine.\n• Linux: SimHub no soporta Linux/SteamOS nativamente (foro oficial: 'SimHub does not currently support Linux or Steam OS natively'); corre bajo wine/Bottles con dotnet48 (guías del propio foro). Bajo wine funcionan salidas serie (Arduino) y audio (shakers) — caso GT4 validado en nuestro rig — pero NO hay salida evdev/gamepad ni com0com; tampoco existe vía evdev para inyectar rumble a mandos desde SimHub.",
  "enfoques_linux_ff": "Tres vías para inyectar FF en Linux, con cifras realistas:\n• SDL haptic (C/C++): SDL_HapticRumblePlay(haptic, strength 0-1, length ms) — fuego y olvido; en Linux SDL implementa sobre evdev FF; strength tope 1.0 (no amplifica); gain global vía SDL_HAPTIC_GAIN. Frecuencia: la que marque la app (60 Hz por frame es viable); el límite real es driver/motor.\n• evdev FF (kernel): subir efectos con EVIOCSFF (FF_RUMBLE strong/weak 0x0000–0xFFFF), reproducir con write(), FF_GAIN (EVIOCSGAIN) para ganancia persistente — solo atenúa (máx 0xFFFF=100%). Doc oficial: kernel.org 'Force feedback for Linux'. En el Go S el driver es xpad+ff-memless: el kernel aplica gain = magnitud*gain/0xffff y los updates de envelope van a FF_ENVELOPE_INTERVAL = 50 ms (20 Hz) — fuente: drivers/input/ff-memless.c; EVIOCSGAIN re-aplica los efectos al cambiar (sirve para slider de atenuación; precedente: rog-ally-rumble-fixer, que debe re-aplicarlo en loop porque InputPlumber resetea el gain).\n• D-Bus InputPlumber (nuestra vía): org.shadowblip.Output.ForceFeedback en /org/shadowblip/InputPlumber/CompositeDeviceN — Rumble(double 0..1), Stop, Enabled (rw); ejemplo busctl real en issue #706. Medición propia en la Legion Go S (DeckySense, 8-oct-2026): latencia gdbus 13.8–21.8 ms (avg 17.6 ms) y ~20.5 Hz sostenidos → apto para patrones/curvas (RPM, derrapes, pianos por telemetría) pero no para haptics de audio finos. PR #489 ('Scale', draft) sigue sin merge (debate de diseño: source-level vs event-level); PR #729 (routing rumble Go S, haptic pulses, dB gain -24..+6) sigue open.\n• Contexto: los juegos actualizan rumble a 30–60 Hz; motores ERM no rinden modulación útil por encima de ~50 Hz. Para telemetría a 20–60 Hz las tres vías sirven; la D-Bus es la única ya probada en este hardware.",
  "steam_rumble_intensity": "Update localizado y verificado: 'Steam Client Beta - September 10th' (10-sep-2026; el 'grupo 4397053' = Steam Client Beta). Texto exacto, sección 'Steam Controller Firmware': 'Improved rumble emulation and added configurable intensity levels' (además: 'Added a 2nd BLE pairing slot...' y fix de thumbsticks). URL del post: store.steampowered.com/news/group/4397053/view/668376226113519967 (espejo textual: steamdeck.com/en/news?p=4).\n• Qué incluye EXACTAMENTE: firmware/ajustes del Steam Controller (2026) — mejora cómo sus actuadores hápticos EMULAN rumble y añade NIVELES de intensidad configurables. NO es un ajuste general del cliente para cualquier mando (el changelog lo encuadra bajo 'Steam Controller Firmware'; todos los reportes son de usuarios del Steam Controller).\n• Dónde está el ajuste: Biblioteca → juego → botón Opciones → Properties → Controller → 'Rumble Intensity for this game' (mismo sitio donde se desactiva Steam Input) — cita textual del hilo r/SteamController 'Steam Controller Rumble Intensity Options'. Se guarda por juego en localconfig.vdf como 'SteamControllerRumbleIntensity' (default 320). Contexto histórico (misma clave, Steam Controller 2015): niveles Extra Low=16000, Low=8000, Medium Low=1000, Default(Medium)=320, Medium High=200, High=100, Extra High=60, 8-bit=16 — números MENORES = más fuerte; la escala clásica iba en AMBAS direcciones (más suave y más fuerte que el default). Un usuario del mando nuevo editó 320→1920 (experimento; otro reporta que la clave 'changes the frequency of the rumble') y no hay lista pública confirmada de los nuevos niveles.\n• ¿Solo atenúa o amplifica? En el Steam Controller los niveles clásicos permitían reforzar por encima del default (Medium High/High/Extra High/8-bit). Para mandos genéricos ese ajuste no existe.\n• ¿Aplica a mandos genéricos tipo Legion Go S? Sin evidencia de que sí: el update es del Steam Controller; la petición de slider por juego para mandos genéricos (ValveSoftware/steam-for-linux#10129) sigue ABIERTA desde 2023; para genéricos solo hay toggles globales (Settings > Controller > Game Rumble / Steam Haptics on/off). Relacionado para handhelds: el beta del 21-sep-2026 trae 'Fixed regression with rumble on 3rd party SteamOS Handhelds' (aplica a Legion Go S). Caveat: algunos usuarios con cliente+mando actualizados no ven el ajuste ('must be A/B testing').",
  "conclusion_viabilidad": "Viabilidad para DeckySense (haptics ricos/telemetría en la Legion Go S):\n1) Telemetry-to-haptics PS2: sin precedente público → oportunidad pionera y técnicamente viable HOY por tres caminos: (a) D-Bus InputPlumber Rumble/Stop a ~20 Hz con latencia ~17.6 ms — suficiente para RPM/derrape/pianos (ya validado con efectos sintéticos en la consola); (b) inyección FF (uinput/evdev) al pad virtual de Steam (prueba P2 pendiente — daría telemetría 'sin depender del juego'); (c) EVIOCSGAIN sobre event2 para un slider de atenuación real (precedente rog-ally-rumble-fixer; prueba sensorial P1 pendiente).\n2) Amplificar >100%: imposible hoy en kernel/D-Bus/Steam; solo dos boosts reales: firmware del mando (combo Legion L+D-pad ↑/↓: off/low/medium/strong) y, para juegos de PS2, la escala 0–200% por motor del propio PCSX2 (amplifica dentro del emulador). InputPlumber PR #489 (Scale) sigue draft; PR #729 (routing Go S) sigue open → usar feature-detection.\n3) Steam 'configurable intensity levels': es del Steam Controller (2026), no del Go S → no cambia nada para nuestro mando interno (solo toggles globales + fix del 21-sep).\n4) SimHub como puente telemetría→motores del mando: descartado (no implementa salida a gamepads; xboxshakeit es Windows-only; bajo wine solo serie/audio). La telemetría GT4→SimHub sigue sirviendo para shakers/dashboards.\n5) El hueco real (nadie lo cubre): telemetría→motores internos del handheld en SteamOS — DeckySense puede llenarlo vía D-Bus InputPlumber, con el techo de 100% salvo firmware.",
  "fuentes": [
    "https://store.steampowered.com/news/group/4397053/view/668376226113519967",
    "https://www.steamdeck.com/en/news?p=4",
    "https://steamcommunity.com/groups/SteamClientBeta/announcements/",
    "https://www.reddit.com/r/SteamController/comments/1ws41wq/steam_controller_rumble_intensity_options/",
    "https://steamcommunity.com/app/353370/discussions/0/3802778829233916867",
    "https://steamcommunity.com/app/4165870/discussions/0/837249796380210901",
    "https://steamcommunity.com/app/4165870/discussions/0/833873889733989608",
    "https://github.com/ValveSoftware/steam-for-linux/issues/10129",
    "https://github.com/ValveSoftware/steam-for-linux/issues/13303",
    "https://steamdeckhq.com/news/steam-deck-beta-client-gamecube-rumble-support",
    "https://www.simhubdash.com/community-2/simhub-support/control-rumble-motors-via-gamecontroller",
    "https://github.com/SHWotever/SimHub/wiki/ShakeIt-V3-Motors---Output-Configuration",
    "https://github.com/tocaedit/xboxshakeit",
    "https://www.simhubdash.com/community-2/forum/steam-os-support",
    "https://www.simhubdash.com/community-2/simhub-support/guide-simhub-on-linux",
    "https://manual.simhubdash.com/external-sim-integration.md",
    "https://github.com/SHWotever/SimHub/releases",
    "https://github.com/PCSX2/pcsx2/blob/master/pcsx2/SIO/Pad/PadDualshock2.cpp",
    "https://github.com/PCSX2/pcsx2/issues/9622",
    "https://pcsx2.net/docs/configuration/controllers",
    "https://www.gtplanet.net/forum/threads/pcsx2-controller-vibrates-all-the-time.427113",
    "https://github.com/PCSX2/pcsx2/issues/14929",
    "https://github.com/EmuELEC/EmuELEC/issues/975",
    "https://github.com/libretro/RetroArch/issues/16896",
    "https://forums.dolphin-emu.org/Thread-vibration-on-controller-w-script",
    "https://github.com/ARMSX2/ARMSX2/issues/241",
    "https://github.com/elenhinan/ESPTurismo",
    "https://github.com/AlteredAJ/dualsense-haptics",
    "https://github.com/intiface/intiface-console-game-haptics-router",
    "https://www.kernel.org/doc/html/latest/input/ff.html",
    "https://wiki.libsdl.org/SDL2/SDL_HapticRumblePlay",
    "https://raw.githubusercontent.com/torvalds/linux/master/drivers/input/ff-memless.c",
    "https://github.com/ShadowBlip/InputPlumber",
    "https://shadowblip.github.io/InputPlumber",
    "https://github.com/ShadowBlip/InputPlumber/issues/706",
    "https://github.com/ShadowBlip/InputPlumber/pull/489",
    "https://github.com/ShadowBlip/InputPlumber/pull/729",
    "https://github.com/Heric-Olier/DeckySense",
    "https://github.com/alicerum/rog-ally-rumble-fixer",
    "https://github.com/Rayekkk/LeGo-Vibe-Control",
    "https://github.com/piyush-tyagi-13/ally-vibe-control",
    "https://github.com/dawidmpunkt/RumbleDeck",
    "https://github.com/hhd-dev/hhd/issues/206",
    "https://github.com/hhd-dev/hhd/issues/301",
    "https://github.com/mescon/logitech-trueforce-linux-driver"
  ]
}
```
