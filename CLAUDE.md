# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 👤 Modo de trabajo con el dueño del proyecto
- El dueño es ingeniero de datos (Python/SQL), no dev de web/apps. Quiere APRENDER.
- Explicá la estructura y el porqué ANTES de escribir código.
- Avanzá paso a paso, no generes módulos enteros de una sin comentar qué hace cada parte.
- En temas .NET/Windows/frontend podés ser más autónomo; en Flask/API/arquitectura, modo enseñanza.
- **No usar plan mode ni AskUserQuestion de forma forzada.** El usuario planifica con otro modelo y ejecuta con Sonnet. Hacer preguntas directamente en texto.

---

## 🖥️ Comandos de Desarrollo

El proyecto usa Python 3.12 con `uv`. Ejecutar siempre desde la raíz del proyecto.

```powershell
# Instalar dependencias
uv sync

# Iniciar el servidor
uv run python main.py

# Probar los sensores de forma aislada (sin Flask)
uv run python -m src.sensors.sensors

# Acceder al panel desde el navegador local
# http://localhost:7842
# Desde la tablet (reemplazar con la IP real del PC)
# http://192.168.x.x:7842
```

No hay tests automatizados. La validación se hace ejecutando el servidor y comprobando las métricas en el navegador o revisando la salida de consola de `sensors.py`.

---

## 🏗️ Arquitectura Actual (implementada)

```
[Hilo sensor cada ~2s] → [dict caché en memoria] → [Flask SSE /stream]       → [EventSource en tablet]
[Hilo audio cada 100ms] → [buffer FFT numpy]     → [Flask SSE /stream/audio] → [EventSource en tablet]
```

| Capa | Archivo | Estado |
|---|---|---|
| Entry point | `main.py` | `waitress` en producción, 4 threads |
| Servidor Flask | `src/server/app.py` | Rutas `/`, `/stream`, `/stream/audio`, `/avatar/*`, `/media/<action>` |
| Sensores | `src/sensors/sensors.py` | `psutil` (CPU/RAM), subprocess a exe C# (GPU), ctypes RTSS (FPS), winsdk (multimedia + control) |
| Audio | `src/sensors/audio.py` | WASAPI loopback via `sounddevice`, FFT via `numpy`, 8 bandas 0–100 |
| GPU exe | `tools/bin/gpu_sensor.exe` | C# .NET 9 + LibreHardwareMonitor, imprime JSON a stdout |
| Frontend | `web/templates/index.html` | HUD NEURAL GRID, SSE dual (telemetría + audio), Jarvis visualizer, controles multimedia, avatar |
| Estilos | `web/static/style.css` | CSS oscuro optimizado para 1280×800, neon border-snake buttons |
| Avatar | `avatar/` | PNGs con fondo transparente, servidos dinámicamente, rotan cada 3 min |
| Despliegue | `scripts/install_task.ps1` | Task Scheduler at logon (sesión usuario, multimedia + audio loopback funcionan) |

---

## 📌 Visión General

Panel web de telemetría de PC en **tiempo real** para una **tablet vía WiFi (red local)**. Muestra CPU, RAM, GPU AMD Radeon RX 7800 XT, FPS (via RTSS), estado multimedia con controles de reproducción, y visualizador de audio reactivo (Jarvis arc-reactor). Opera de forma silenciosa en Windows, sin impactar el rendimiento del PC host.

**Cliente:** Huawei MediaPad 10 (10.1", 1280×800, landscape), Android 4.1, Firefox 68.11.0 (Gecko/2019). Soporta ES6 completo, `fetch`, `EventSource`, CSS Grid, `async/await`.

---

## ⚠️ Restricciones Críticas del Cliente

Es un MediaPad del 2013 con CPU y RAM limitadas funcionando como monitor permanente.

- **SSE sobre polling.** Un solo `EventSource` abierto es más eficiente que un request HTTP por segundo.
- **DOM mínimo.** Actualizar solo los nodos que cambian, nunca re-renderizar tarjetas enteras.
- **Sin librerías JS externas** (no jQuery, no React, no Chart.js). Vanilla JS puro.
- **Sin animaciones CSS pesadas.** Solo `transform` (GPU-accelerated) y `opacity`. Sin blur en elementos grandes.
- **Canvas Jarvis a 20 fps** — suficiente para reactividad al audio, no satura el MediaPad.
- **Fondo oscuro** para lectura continua y ahorro de batería.
- **Reconexión automática:** el cliente reconecta el `EventSource` sin intervención manual (setTimeout 3000ms en onerror).

---

## 🔧 Stack y Decisiones de Sensores

- **CPU/RAM:** `psutil` — `psutil.cpu_percent(interval=None)` y `psutil.virtual_memory()`. Sin subprocess a PowerShell.
- **GPU/Temp:** exe C# (`tools/bin/gpu_sensor.exe`) usando `LibreHardwareMonitor` como NuGet. Python lo llama via `subprocess` en cada ciclo. Imprime `{"gpu_usage": X, "gpu_temp": Y}` a stdout. Requiere .NET 9 Runtime.
- **FPS:** RTSS shared memory `RTSSSharedMemoryV2` via `ctypes`. Fallback a `GetDeviceCaps(VREFRESH)` cuando no hay juego activo. Campo `fps_source` indica `"game"` o `"display"`.
- **Multimedia:** `winsdk` (GSMTC). Devuelve estado y metadatos. El control (prev/play-pause/next) también usa GSMTC via `session.try_skip_previous_async()` etc. Requiere sesión de usuario (no Sesión 0).
- **Audio:** `sounddevice` con WASAPI loopback — captura lo que suena en el sistema sin micrófono. `numpy.fft.rfft` sobre ventanas de 2048 samples. Resultado: 8 bandas normalizadas 0–100.
- **Threading multimedia:** `_media_lock = threading.Lock()` protege el event loop de asyncio compartido entre el hilo sensor y los requests Flask de `/media/<action>`.
- **Servidor de producción:** `waitress` (WSGI puro en Windows). `app.run()` de Flask solo para debug manual.
- **Despliegue:** Task Scheduler con trigger de logon. `LogonType Interactive` + `RunLevel Highest` — corre en la sesión del usuario con permisos de admin (necesario para LibreHardwareMonitor y WASAPI loopback).

---

## 📊 Payload SSE — `/stream` (estructura fija)

Todos los campos presentes en cada emisión; fallback `0.0` / `""` si falla una lectura:

```json
{
  "cpu_load": 34.7,
  "ram_total": 32.0,
  "ram_used": 18.4,
  "ram_percent": 57.5,
  "gpu_usage": 81.0,
  "gpu_temp": 72.0,
  "fps": 144.0,
  "fps_source": "game",
  "media_status": "Reproduciendo",
  "media_title": "Artista · Título · Fuente"
}
```

`fps_source` es `"game"` cuando RTSS reporta FPS activos, `"display"` cuando devuelve el refresh rate del monitor como fallback. El frontend cambia la etiqueta entre "FPS" y "Hz" según este campo.

## Payload SSE — `/stream/audio`

Array de 8 floats, cada ~100ms:

```json
[0.0, 42.3, 78.1, 55.0, 30.2, 18.4, 8.7, 3.1]
```

Bandas 0 y 2 suelen ser 0 (DC / artefactos de filtro). El visualizador Jarvis usa bandas 1, 3, 4 para beat detection.

---

## 🎛️ Visualizador Jarvis

Canvas 2D reactivo al audio. Parámetros ajustables en `index.html` (objeto `JARVIS`):

```javascript
var JARVIS = {
    coreSpeed:     1.0,  // velocidad rotación arc central  (0.5 lento – 3.0 rápido)
    particleCount: 28,   // cantidad de partículas orbitando (10 – 80)
    particleSpeed: 1.0,  // velocidad base de las partículas (0.3 lento – 2.5 rápido)
    fps:           20,   // frames por segundo del canvas    (15 – 60)
};
```

Beat detection adaptativo: `bass > avgBass * 1.30` — detecta spikes relativos al nivel reciente, no un umbral absoluto. Evita falsos negativos en canciones quietas y falsos positivos en canciones fuertes.

---

## 🗺️ Mapa de Ruta

### ✅ Fase 1: Fundaciones
- [x] Estructura del proyecto (`src/server`, `src/sensors`, `web/`).
- [x] Servidor Flask base.
- [x] Migración de WSL2 a Windows nativo.

### ✅ Fase 2: Sensores Base
- [x] Módulo `sensors.py` aislado.
- [x] CPU/RAM con `psutil`.
- [x] Hilo de caché en background.
- [x] Caché conectado al stream SSE.

### ✅ Fase 3: GPU
- [x] Exe C# con LibreHardwareMonitor.
- [x] Uso (%) y temperatura de la RX 7800 XT.

### ✅ Fase 4: Multimedia e Interfaz Final
- [x] Endpoint SSE Flask (`text/event-stream`).
- [x] Frontend NEURAL GRID: CSS oscuro, tarjetas HUD, optimizado para 1280×800.
- [x] JS: `EventSource` con reconexión automática, actualización de nodos individuales.
- [x] FPS via RTSS + fallback refresh rate de monitor.
- [x] Multimedia: `winsdk` GSMTC (estado + metadatos).
- [x] Avatar: PNGs en `avatar/`, servidos dinámicamente, rotación cada 3 min con fade.

### ✅ Fase 5: Producción
- [x] Reemplazar `app.run()` por `waitress`.
- [x] Task Scheduler con logon trigger.
- [x] Scripts `install_task.ps1` y `uninstall_task.ps1`.

### ✅ Fase 6: Audio y Visualizador
- [x] `audio.py`: captura WASAPI loopback, FFT, 8 bandas normalizadas.
- [x] `/stream/audio`: SSE separado cada 100ms.
- [x] Visualizador Jarvis: canvas 2D arc-reactor reactivo al audio.
- [x] Beat detection adaptativo (umbral relativo al promedio reciente).
- [x] Controles multimedia: prev / play-pause / next via GSMTC.
- [x] Endpoint `/media/<action>` (POST, 204).
- [x] Botones con efecto neon border-snake (CSS puro, sin librerías).
- [x] Layout vertical: Jarvis → artista → título → controles → avatar.

---

## 🛠️ Reglas de Desarrollo

1. **Hardware real:** leer sensores nativos, no mocks ni entornos virtuales.
2. **Lecturas ligeras:** `psutil` para CPU/RAM, exe C# para GPU. Sin PowerShell en cada poll.
3. **Caché siempre:** el stream SSE lee del diccionario en memoria, nunca directamente del hardware.
4. **Resiliencia:** toda función sensora lleva `try/except` y devuelve `0.0`.
5. **Frontend liviano:** sin librerías externas, DOM mínimo, solo `transform` y `opacity` como animaciones CSS.
6. **SSE sobre polling.**
7. **Producción ≠ desarrollo:** `waitress` para servir, nunca el servidor de Flask.
8. **Avatar dinámico:** la lista de imágenes se lee de `/avatar/list` al cargar — no hardcodear nombres en el JS.
9. **Canvas a 20 fps:** no superar sin motivo claro — el MediaPad tiene recursos limitados.
10. **Threading multimedia:** usar `_media_lock` al acceder al event loop de asyncio desde hilos de Flask.
