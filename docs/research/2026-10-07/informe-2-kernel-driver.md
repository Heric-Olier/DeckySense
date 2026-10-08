# Informe: soporte de rumble/haptics en el kernel Linux — Lenovo Legion Go / Go S (para DeckySense)

**Analizado:** 7 oct 2026 · **Objetivo:** driver `hid-lenovo-go` / `hid-lenovo-go-s` (Derek J. Clark) y su estado en mainline y en SteamOS 3.8.x (kernel 6.16.12-valve, neptune-616).

## TL;DR (lo esencial para un plugin Decky en Legion Go S)

- 🔴 **Legion Go S:** el driver del kernel (`hid-lenovo-go-s`) **no expone ningún control de rumble/haptics**. Verificado en el código final v7.1: 0 menciones de `rumble`, `vibration` o `haptic`; y en ninguna revisión de la serie (v1–v6) existe un patch de rumble para el Go S. No hay "versión con haptic settings" que buscar en su `.ko`.
- 🟢 **Legion Go / Go 2:** el driver `hid-lenovo-go` sí expone sysfs: `rumble_intensity` (off/low/medium/high), `left_handle` y `right_handle/rumble_mode` (fps/racing/standard/spg/rpg), `rumble_notification` (true/false) y `touchpad/vibration_enabled` + `touchpad/vibration_intensity` (off/low/medium/high). No hay ioctls ni atributo `haptic_mode`.
- 📦 **Mainline:** la serie se mergeó para **Linux 7.1** (aceptada por Jiri Kosina el 10-11 mar 2026: "This is now in hid.git#for-7.1/lenovo-v2"; tag `v7.1` del 14 jun 2026). **No está** en 6.16, 6.17, 6.18 ni 7.0.
- 🎮 **SteamOS 3.8.x / kernel 6.16.12-valve:** el 6.16 mainline no contiene el driver ⇒ lo que corre en la consola es un **backport de Valve** (los archivos llevan "Copyright (c) 2026 Valve Corporation" junto a Clark). Para el **Go S no cambia nada** (su driver nunca tuvo rumble). Para `hid-lenovo-go` (Go/Go2) se verifica con `strings` si el backport trae los atributos.
- 🛠️ **Implicación:** en el Go S, la única vía kernel hoy es FF/evdev — el gamepad lo maneja `xpad` (USB `0x1a86:0xe310`, XTYPE_XBOX360) — y la intensidad del MCU no está expuesta (solo se ajusta desde Legion Space/Windows según reportes de usuarios). Vigilar la "later patch series" que el autor anunció para mover funciones avanzadas (hoy en InputPlumber) al kernel.

## (a) Los parches "Add Rumble and Haptic Settings"

Serie: **"[PATCH vN] HID: Add Legion Go and Go S Drivers"** — Derek J. Clark `<derekjohn.clark@gmail.com>` (revisores: Mark Pearson, Jiri Kosina; lista linux-input).

| Rev | Fecha | Patches | ¿Patch de rumble? | Enlace |
|---|---|---|---|---|
| v1 | 2025-07-03 | 6 | No (solo "HID: Add Legion Go S Driver"; 0 menciones de rumble) | https://lore.kernel.org/linux-input/20250703004943.515919-1-derekjohn.clark@gmail.com/ |
| v2 | 2025-12-29 | 16 | **Sí** — "HID: hid-lenovo-go: Add Rumble and Haptic Settings" (04/16) | https://lore.kernel.org/lkml/20251229031753.581664-1-derekjohn.clark@gmail.com/ |
| v3 | 2026-01-24 | 16 | Sí (mismo patch) | https://lore.kernel.org/linux-input/20260124014907.991265-1-derekjohn.clark@gmail.com/ |
| v4 | 2026-02-20 | 16 | Sí | https://lore.kernel.org/linux-input/20260220070533.4083667-1-derekjohn.clark@gmail.com/ |
| v5 | 2026-02-24 | 16 | Sí | https://lore.kernel.org/linux-input/20260224013217.1363996-1-derekjohn.clark@gmail.com/ |
| v6 | 2026-03-10 | 19 | Sí (04/19) — **versión final mergeada** | https://lore.kernel.org/linux-input/20260310072937.3295875-1-derekjohn.clark@gmail.com/ |

Enlaces directos al patch final (v6, 04/19): https://lore.kernel.org/linux-input/20260310072937.3295875-5-derekjohn.clark@gmail.com/ y https://patchew.org/linux/20260310072937.3295875-1-derekjohn.clark@gmail.com/20260310072937.3295875-5-derekjohn.clark@gmail.com (v5 en patchew: .../20260224013217.1363996-5-...; patchwork: https://patchwork.kernel.org/project/linux-input/list/?q=lenovo-go; spinics espeja la lista: p.ej. https://www.spinics.net/lists/kernel/msg6068338.html).

Resumen del patch (texto del commit): *"Adds attributes that control the handles rumble mode and intensity, as well as touchpad haptic feedback settings."* (Reviewed-by: Mark Pearson). Nota: no existe ningún patch titulado "Add rumble and haptic settings support"; el título exacto es el de arriba, y es del driver del **Go/Go2**, no del Go S.

### Atributos exactos expuestos (100% sysfs; no hay ioctls; no existe `haptic_mode`)

Ubicación: en el `hid_device` (`/sys/bus/hid/devices/0003:VID:PID.NNNN/...`; documentado como `/sys/bus/usb/devices/<...>/<hid-bus>:<vid>:<pid>.<num>/...`). Los grupos con nombre crean subdirectorio (`left_handle/`, `right_handle/`, `touchpad/`).

| Atributo | Acceso | Valores legales | Notas |
|---|---|---|---|
| `rumble_intensity` + `rumble_intensity_index` | RW / RO | `off`, `low`, `medium`, `high` | Intensidad global de ambos mandos; a nivel raíz del device |
| `left_handle/rumble_mode` y `right_handle/rumble_mode` + `*_index` | RW / RO | `fps`, `racing`, `standard`, `spg`, `rpg` | "response behavior for rumble events" por mango (perfil/curva del firmware) |
| `left_handle/rumble_notification` y `right_handle/rumble_notification` + `*_index` | RW / RO | `true`, `false` | Habilita eventos de rumble háptico por mango |
| `touchpad/vibration_enabled` + `*_index` | RW / RO | `true`, `false` | Haptics del touchpad |
| `touchpad/vibration_intensity` + `*_index` | RW / RO | `off`, `low`, `medium`, `high` | Intensidad del touchpad (independiente de los mandos) |

Detalles verificados:
- Los `*_index` (RO) listan las opciones válidas (userspace los lee para autodescubrimiento — así lo hace el plugin comunitario LeGo-Vibe-Control).
- Internamente el índice 0 = "unknown"; los strings aceptados empiezan en 1.
- El ABI doc oficial dice "Values are fps, racing, standarg, spg, rpg" — **"standarg" es un typo del doc**; el código y los índices usan `standard`.
- Comportamiento conocido (README del plugin LeGo-Vibe-Control): `rumble_intensity` puede devolver en lectura el valor *anterior* a la última escritura → cachear lo escrito y reescribir tras suspend/reconexión.
- Todos los atributos dicen en el ABI: "Applies to Lenovo Legion Go and Go 2 line of handheld devices" — **ninguno aplica al Go S**.

### ¿Y el Go S en los parches?

- v1 (jul-2025, serie solo del Go S): 0 menciones de rumble/vibration/haptic (verificado en el mbox completo).
- v2–v6: los patches del Go S son: driver base, MCU ID, Feature Status, Touchpad Mode, RGB, IMU/TP RO — **ninguno de rumble**. El código final v7.1 de `hid-lenovo-go-s.c` no contiene las palabras rumble/vibration/haptic (grep = 0).
- El driver del Go (`hid-lenovo-go`) solo matchea los PIDs nuevos `0x17aa:0x61eb/0x61ec/0x61ed/0x61ee` (Go y Go 2 con firmware actualizado). Cita del autor (patch v2): *"the PIDs for the controllers were changed, so there is no risk of this driver attaching to controller firmware that it doesn't support"*. El Go S usa IDs distintos (vendor QHE `0x1a86:0xe310/0xe311`) y **no matchea este driver**.

## (b) ¿Mergeado en mainline? ¿Qué hay en SteamOS?

**Mainline: SÍ — Linux 7.1.**
- Jiri Kosina (mantenedor HID), sobre v6 (10-11 mar 2026): *"This is now in hid.git#for-7.1/lenovo-v2."*
- Verificado en los tags de git.kernel.org: en `v7.1` (14 jun 2026; Makefile 7.1.0, nombre "Baby Opossum Posse") existen `drivers/hid/hid-lenovo-go.c`, `drivers/hid/hid-lenovo-go-s.c` y `Documentation/ABI/testing/sysfs-driver-hid-lenovo-go{,-s}`; en `v7.0`, `v6.18`, `v6.17` y `v6.16` devuelven 404 (no existen).
- Commits en 7.1: "HID: hid-lenovo-go: Add Rumble and Haptic Settings" (2026-03-10) + fixes durante el ciclo: "HID: hid-lenovo-go-s: restore OS_TYPE after resume from s2idle" (2026-04-28), "HID: lenovo-go: reject non-USB transports in probe" y "drop dead NULL check" (2026-05-21). En master hay además "cancel cfg_setup work in hid_go_cfg_remove()" (2026-06-03). **Hasta hoy no existe ningún parche que añada rumble al go-s.**

**SteamOS 3.8.x / kernel 6.16.12-valve (neptune-616):**
- El 6.16 mainline NO tiene los drivers ⇒ lo que corre en la consola es **backport de Valve**. Evidencia: (1) ausencia en mainline 6.16 (verificado); (2) SteamOS 3.8 anuncia "Added controller RGB LED color settings for the Lenovo Legion Go 2" — interfaz LED del mismo driver; (3) ambos archivos llevan "Copyright (c) 2026 Valve Corporation" (co-desarrollo); (4) los `.ko` están presentes en la consola.
- Respuesta a "¿versión con haptic settings o solo la básica?": en el driver del **Go S no existe ninguna variante con haptic settings** (nada que buscar). En `hid-lenovo-go` (Go/Go2) se verifica con los comandos (strings + sysfs): si el `.ko` contiene `rumble_intensity`, `rumble_mode`, `rumble_notification`, `vibration_enabled`, `vibration_intensity` y los valores `off/low/medium/high` + `fps/racing/standard/spg/rpg`, el backport incluye la feature completa (esperable: Valve tomó la serie final v5/v6).
- Evidencia de campo independiente (plugin Decky comunitario "LeGo-Vibe-Control", mismo concepto que DeckySense): *"Legion Go S is not supported. Its hid-lenovo-go-s driver does not expose vibration control via sysfs (as of May 14, 2026, SteamOS 3.9)."* — y para Go/Go2 requiere "SteamOS 3.8+ / Kernel 6.18+".

## (c) ¿Qué soporta el MCU? (intensidad global vs forma de onda/frecuencia)

- **Go / Go 2** (lo que el kernel expone): intensidad global (4 niveles), perfil de respuesta de rumble por mango (5 modos), habilitación de notificación por mango y haptics del touchpad (on/off + 4 niveles). **No hay forma de onda ni frecuencia programable por motor**: son parámetros de alto nivel ("response behavior for rumble events", "rumble intensity for both removable controllers"); la señal la genera el firmware/MCU.
- **Go S:** el kernel (cualquier versión) **no expone ningún control de motor**. Evidencia de campo (r/LegionGo, feb-2026): la intensidad del Go S se ajusta solo desde Windows/Legion Space (*"change the vibration intensity to weak and voila... you need to boot to windows to change it back in legion space again"*) y persiste en el firmware; en SteamOS no hay interfaz. El rumble de juegos llega por FF estándar del gamepad (xpad). Sin evidencia de waveform/frecuencia configurable por motor en ninguna interfaz.
- **Futuro:** cover letter de la serie (v6): *"Basic gamepad functionality is provided through xpad, while advanced features are currently only implemented in userspace daemons such as InputPlumber. I plan to move this functionality into the kernel in a later patch series."*

## (d) Verificación en la Legion Go S real (SSH) — comandos al final

Guía de interpretación:
- Go S (esperado): `hid-lenovo-go-s` bindeado al device `0003:1A86:E310.*` / `:E311.*`; atributos `gamepad/`, `imu/`, `mouse/`, `touchpad/` (enabled, linux_mode, windows_mode), `mcu_id`, `os_mode`, y LEDs `go_s:rgb:joystick_rings`; **sin** `rumble*`/`vibration*`; strings del `.ko` para rumble/vibration/haptic = vacío.
- `hid-lenovo-go` (Go/Go2): si el backport incluye la feature, el `.ko` mostrará `rumble_intensity`, `rumble_mode`, `rumble_notification`, `vibration_enabled`, `vibration_intensity` y los valores. Si no aparecen, el backport es "solo la parte básica".
- Recordar: el device del Go S NO matchea `hid-lenovo-go` → no esperar `rumble_intensity` en sysfs del Go S aunque ese `.ko` exista en el sistema.

Comandos (lista completa también en `comandos_verificacion_ssh`):

```bash
uname -r && cat /etc/os-release | head -5
modinfo hid-lenovo-go-s 2>/dev/null | grep -E '^(filename|description|author|license|alias)'
modinfo hid-lenovo-go 2>/dev/null | grep -E '^(filename|description|author|license|alias)'
lsmod | grep -i lenovo; echo '---'; ls /sys/module | grep -i lenovo
ls /sys/bus/hid/drivers/ | grep -i lenovo
ls -l /sys/bus/hid/drivers/hid-lenovo-go-s/ /sys/bus/hid/drivers/hid-lenovo-go/ 2>/dev/null
grep -H '' /sys/bus/hid/devices/*/uevent 2>/dev/null | grep -E 'HID_NAME|HID_ID'
ls -l /sys/bus/hid/devices/*/driver 2>/dev/null
for d in /sys/bus/hid/devices/*1A86*; do echo "== $d"; ls "$d"; done 2>/dev/null
find /sys/bus/hid/devices -maxdepth 2 -iname '*rumble*' 2>/dev/null
find /sys/bus/hid/devices -maxdepth 2 -iname '*vibration*' 2>/dev/null
KO=$(modinfo -F filename hid-lenovo-go-s); { case "$KO" in *.zst) zstdcat "$KO" ;; *) cat "$KO" ;; esac; } | strings -a | grep -iE 'rumble|vibration|haptic' | sort -u
KO=$(modinfo -F filename hid-lenovo-go); { case "$KO" in *.zst) zstdcat "$KO" ;; *) cat "$KO" ;; esac; } | strings -a | grep -iE 'rumble|vibration|haptic' | sort -u
cat /sys/bus/hid/devices/*/rumble_intensity_index 2>/dev/null
cat /sys/bus/hid/devices/*/left_handle/rumble_mode_index 2>/dev/null
grep -B1 -A6 -iE 'legion|x-box|xbox' /proc/bus/input/devices | head -80
for e in /sys/class/input/event*; do n=$(cat "$e/device/name" 2>/dev/null); case "$n" in *egion*|*X-Box*|*Xbox*) echo "$e :: $n :: ff=$(cat "$e/device/capabilities/ff" 2>/dev/null)";; esac; done
lsusb | grep -iE '1a86|17aa|lenovo'
sudo dmesg | grep -iE 'hid-lenovo|lenovo-go|legion' | tail -40
ls /usr/src/ 2>/dev/null; ls /lib/modules/$(uname -r)/build 2>/dev/null | head -5
find /usr/src /lib/modules/$(uname -r) -maxdepth 5 -iname '*lenovo-go*' 2>/dev/null
curl -sL 'https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/plain/drivers/hid/hid-lenovo-go-s.c?h=v7.1' | grep -ciE 'rumble|vibration|haptic'
curl -sL 'https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/plain/drivers/hid/hid-lenovo-go.c?h=v7.1' | grep -nE 'rumble_intensity|rumble_mode|rumble_notification' | head -10
```

## Fuentes principales

- Patches (lore): v6 cover https://lore.kernel.org/linux-input/20260310072937.3295875-1-derekjohn.clark@gmail.com/ · v2 cover https://lore.kernel.org/lkml/20251229031753.581664-1-derekjohn.clark@gmail.com/ · v1 https://lore.kernel.org/linux-input/20250703004943.515919-1-derekjohn.clark@gmail.com/
- Patchew (con diffs completos): https://patchew.org/linux/20260310072937.3295875-1-derekjohn.clark@gmail.com/ y patch 04/19 https://patchew.org/linux/20260310072937.3295875-1-derekjohn.clark@gmail.com/20260310072937.3295875-5-derekjohn.clark@gmail.com/
- Patchwork: https://patchwork.kernel.org/project/linux-input/list/?q=lenovo-go · Spinics (espejo LKML): https://www.spinics.net/lists/kernel/msg6068338.html
- Código final (tag v7.1): https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/hid/hid-lenovo-go.c?h=v7.1 y .../hid-lenovo-go-s.c?h=v7.1 · ABI docs: .../Documentation/ABI/testing/sysfs-driver-hid-lenovo-go{,-s}?h=v7.1
- Phoronix: https://www.phoronix.com/news/Legion-Go-Controller-HID-v2 y https://www.phoronix.com/news/Lenovo-Legion-Go-S-HID
- Plugin comunitario (evidencia de campo): https://github.com/Rayekkk/LeGo-Vibe-Control (README: atributos, límites y "Legion Go S is not supported")
- Reddit (MCU Go S, ajuste solo en Windows): https://www.reddit.com/r/LegionGo/comments/1r50my8/legion_go_s_loud_shoulder_buttons_and_vibration/
- SteamOS 3.8 changelog: https://www.gamingonlinux.com/2026/06/steamos-3-8-is-out-with-initial-steam-machine-support-desktop-mode-upgrades-new-graphics-drivers
