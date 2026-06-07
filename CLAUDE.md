# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 👤 Modo de trabajo con el dueño del proyecto
- El dueño es ingeniero de datos (Python/SQL), no dev de web/apps. Quiere APRENDER.
- Explicá la estructura y el porqué ANTES de escribir código.
- Avanzá paso a paso, no generes módulos enteros de una sin comentar qué hace cada parte.
- En temas .NET/Windows/frontend podés ser más autónomo; en Flask/API/arquitectura, modo enseñanza.

---

## 🖥️ Comandos de Desarrollo

El proyecto usa Python 3.12 con un virtualenv en `.venv/`. Ejecutar siempre desde la raíz del proyecto.

```powershell
# Activar entorno virtual (Windows)
.venv\Scripts\activate

# Iniciar el servidor de desarrollo
python main.py

# Probar los sensores de forma aislada (sin Flask)
python -m src.sensors.sensors

# Acceder al panel desde el navegador local
# http://localhost:8090
# Desde la tablet (reemplazar con la IP real del PC)
# http://192.168.x.x:8090
```

No hay tests automatizados. La validación se hace ejecutando el servidor y comprobando las métricas en el navegador o revisando la salida de consola de `sensors.py`.

---

## 🏗️ Arquitectura Actual vs. Arquitectura Objetivo

> **Estado actual del código:** el MVP funciona pero todavía no implementa la arquitectura final. Hay brecha entre lo que está en el código y lo que dice este documento como objetivo.

### Estado actual (código real hoy)

| Capa | Archivo | Estado |
|---|---|---|
| Entry point | `main.py` | Ejecuta `app.run()` (modo dev). Incluye código residual del puente WSL2 que ya no aplica. |
| Servidor Flask | `src/server/app.py` | Ruta `/` renderiza `index.html` con Jinja2. Lee sensores **en cada request HTTP** (sin caché, sin SSE). |
| Sensores | `src/sensors/sensors.py` | Usa `subprocess` + `powershell.exe` para CPU, RAM y GPU. **Pendiente migrar a `psutil`**. |
| Frontend | `web/templates/index.html` | MVP básico con `<meta http-equiv="refresh" content="3">`. **Pendiente migrar a SSE + EventSource**. |
| Estilos | `web/static/style.css` | CSS mínimo de placeholder. |

### Arquitectura objetivo

```
[Hilo sensor cada ~2s] → [dict caché en memoria] → [Flask SSE stream] → [EventSource en tablet]
```

Un **hilo en background** lee los sensores a ritmo fijo y actualiza un diccionario en memoria. La ruta SSE de Flask lee ese diccionario y empuja datos al cliente. Las peticiones HTTP **nunca disparan lecturas de hardware directas**.

---

## 📌 Visión General

Panel web de telemetría de PC en **tiempo real** para una **tablet vía WiFi (red local)**. Muestra CPU, RAM, GPU AMD Radeon RX 7800 XT y estado multimedia. Opera de forma silenciosa y nativa en Windows, sin impactar el rendimiento del PC host.

**Cliente:** Huawei MediaPad 10 (10.1", 1280×800, landscape), Android 4.1, Firefox 68.11.0 (Gecko/2019). Soporta ES6 completo, `fetch`, `EventSource`, CSS Grid, `async/await`. No necesita ES5 ni `XMLHttpRequest`.

---

## ⚠️ Restricciones Críticas del Cliente

Es un MediaPad del 2013 con CPU y RAM limitadas funcionando como monitor permanente.

- **SSE sobre polling.** Un solo `EventSource` abierto es más eficiente que un request HTTP por segundo.
- **DOM mínimo.** Actualizar solo los nodos que cambian, nunca re-renderizar tarjetas enteras.
- **Sin librerías JS externas** (no jQuery, no React, no Chart.js). Vanilla JS puro.
- **Sin animaciones CSS pesadas** (keyframes, blur, box-shadow excesivo). Efectos sutiles con `will-change`.
- **Fondo oscuro** para lectura continua y ahorro de batería.
- **Reconexión automática:** el cliente debe reconectar el `EventSource` sin intervención manual.

---

## 🔧 Stack y Decisiones de Sensores

- **CPU/RAM:** `psutil` — `psutil.cpu_percent()` y `psutil.virtual_memory()`. **NO** `subprocess` a PowerShell (lento, golpea rendimiento). *Todavía no migrado en el código actual.*
- **GPU/Temp:** `OpenHardwareMonitorLib.dll` vía `pythonnet` (`import clr`). Objeto `Computer` → `GPUEnabled` → recorrer árbol de sensores para uso (%) y temperatura de la RX 7800 XT.
  - *Fallback:* WMI namespace `root\OpenHardwareMonitor` (distinto de `root\LibreHardwareMonitor`).
- **Multimedia:** `winsdk` (GSMTC — `GlobalSystemMediaTransportControlsSessionManager`).
  - ⚠️ **Gotcha Sesión 0:** un servicio NSSM corre en Sesión 0 sin contexto multimedia → devuelve vacío. Solución: Task Scheduler con trigger de logon para la parte multimedia.
- **Servidor de producción:** `waitress` (WSGI puro en Windows). **No** `app.run()` de Flask.
- **Despliegue:** NSSM como servicio silencioso de Windows.

---

## 📊 Payload SSE (estructura fija)

Todos los campos presentes en cada emisión; fallback `0.0` / `""` si falla una lectura:

```json
{
  "cpu_load": 34.7,
  "ram_total": 32.0,
  "ram_used": 18.4,
  "ram_percent": 57.5,
  "gpu_usage": 81.0,
  "gpu_temp": 72.0,
  "fps": 0.0,
  "media_status": "Reproduciendo",
  "media_title": "Infected Mushroom - Converting Vegetarians · YouTube"
}
```

`fps` siempre se incluye como `0.0` hasta que se implemente la lectura real, para no cambiar la estructura del JSON.

---

## 🗺️ Mapa de Ruta

### ✅ Fase 1: Fundaciones
- [x] Estructura del proyecto (`src/server`, `src/sensors`, `web/`).
- [x] Servidor Flask base.
- [x] Migración de WSL2 a Windows nativo.

### 🟡 Fase 2: Sensores Base — REFACTOR PENDIENTE
- [x] Módulo `sensors.py` aislado.
- [ ] Migrar CPU/RAM de PowerShell a `psutil`.
- [ ] Implementar hilo de caché en background.
- [ ] Conectar caché con stream SSE de Flask.

### 🟡 Fase 3: GPU (En Progreso)
- [x] Open Hardware Monitor instalado.
- [ ] Integrar `OpenHardwareMonitorLib.dll` vía `pythonnet`.
- [ ] Extraer uso (%) y temperatura de la RX 7800 XT.

### ⏳ Fase 4: Multimedia e Interfaz Final
- [ ] Endpoint SSE Flask (`text/event-stream`).
- [ ] Frontend: CSS oscuro, tarjetas gamer/tech, optimizado para 1280×800.
- [ ] JS: `EventSource` con reconexión automática, actualización de nodos individuales.
- [ ] Multimedia: `winsdk` GSMTC, resolver gotcha Sesión 0.

### ⏳ Fase 5: Producción
- [ ] Reemplazar `app.run()` por `waitress`.
- [ ] Registrar con NSSM.
- [ ] Resolver multimedia fuera de Sesión 0.

---

## 🛠️ Reglas de Desarrollo

1. **Hardware real:** leer sensores nativos, no mocks ni entornos virtuales.
2. **Lecturas ligeras:** `psutil` para CPU/RAM, DLL nativa para GPU. Sin PowerShell en cada poll.
3. **Caché siempre:** el stream SSE lee del diccionario en memoria, nunca directamente del hardware.
4. **Resiliencia:** toda función sensora lleva `try/except` y devuelve `0.0`.
5. **Frontend liviano:** sin librerías externas, DOM mínimo, sin animaciones pesadas.
6. **SSE sobre polling.**
7. **Producción ≠ desarrollo:** `waitress` para servir, nunca el servidor de Flask.
