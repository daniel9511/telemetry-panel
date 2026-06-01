# 🚀 Panel de Telemetría PC — Contexto del Proyecto (CLAUDE.md)

> Archivo de contexto para Claude Code. Define la visión, arquitectura, restricciones y reglas de desarrollo del proyecto. Léelo completo antes de tocar código.

## 📌 Visión General
Panel web de telemetría de PC en **tiempo real** para visualizarse en una **tablet vía WiFi (red local)**. Muestra métricas vitales del sistema (CPU, RAM), rendimiento gráfico (GPU AMD Radeon RX 7800 XT) y estado multimedia. Debe operar de forma silenciosa y nativa en Windows, sin impactar el rendimiento del PC host.

**Naturaleza del proyecto:** casero / personal. El cliente es una **Huawei MediaPad 10 (10.1", 1280×800, landscape) con Android 4.1 y Firefox 68.11.0 (Fennec/Gecko)**. Esto NO es un servicio comercial: priorizar ligereza, robustez y eficiencia.

---

## ⚠️ Restricciones Críticas del Cliente (LEER PRIMERO)

### Compatibilidad web
Firefox 68 usa su propio motor **Gecko** (no el WebView de Android 4.1), por lo que el OS subyacente es irrelevante para capacidades web. FF 68 (2019) soporta ES6 completo, `fetch`, `EventSource`, CSS Grid, variables CSS, `async/await`, WebSockets, etc.

**No hace falta ES5 ni `XMLHttpRequest`.** Lo que sí importa es:

### Rendimiento y eficiencia (la restricción real)
Es un MediaPad del 2013 con CPU y RAM limitadas funcionando de monitor permanente.

- **Usar Server-Sent Events (SSE) en vez de polling.** Un solo `EventSource` abierto es mucho más eficiente que disparar una petición HTTP nueva cada segundo: menos overhead de red, menos CPU en la tablet, menos batería. El servidor empuja los datos; el cliente solo escucha.
- **DOM mínimo.** Actualizar solo los nodos que cambian (los valores numéricos), nunca re-renderizar tarjetas enteras.
- **Sin animaciones CSS pesadas** (keyframes, blur, box-shadow excesivo, gradientes complejos). Los efectos visuales deben ser sutiles y con `will-change` o aceleración por GPU cuando sea relevante.
- **Sin librerías JS externas** (no jQuery, no React, no Chart.js). Vanilla JS puro para no cargar la memoria del dispositivo.
- **Pantalla siempre encendida:** diseñar para lectura continua. Preferir fondo oscuro (ahorra batería y reduce fatiga visual), tipografía legible a distancia en 10.1" y 1280×800.
- **Sin reconexión manual:** si se pierde la conexión SSE, el cliente debe reconectar automáticamente.

---

## 🏗️ Arquitectura del Sistema

* **Backend:** Python + Flask (modo API / servidor SSE).
* **Servidor de producción:** **`waitress`** (WSGI puro en Python, ideal para Windows). **NO usar `app.run()` de Flask en producción.**
* **Comunicación backend → frontend:** **Server-Sent Events (SSE)**. El servidor abre un stream (`text/event-stream`) y empuja las métricas en JSON cada ~2 segundos. El cliente usa `EventSource`.
* **Frontend:** HTML + CSS + JavaScript Vanilla (ES6 OK). Ver restricciones de rendimiento arriba.
* **Sensores CPU/RAM:** **`psutil`** (`psutil.cpu_percent()`, `psutil.virtual_memory()`). **NO usar `subprocess` a PowerShell para esto** — spawnear PowerShell en cada poll es lento y golpea el rendimiento.
* **Sensores GPU/Temperaturas:** integración directa de **`OpenHardwareMonitorLib.dll`** (.NET) desde Python vía **`pythonnet`** (`import clr`). Crear el objeto `Computer`, habilitar `GPUEnabled`, recorrer el árbol de sensores para extraer uso (%) y temperatura real de la RX 7800 XT.
  * *Fallback:* si la DLL da problemas, leer vía WMI namespace `root\OpenHardwareMonitor` (ojo: Libre Hardware Monitor usa `root\LibreHardwareMonitor` — son distintos).
* **Multimedia:** `winsdk` (GlobalSystemMediaTransportControlsSessionManager) para extraer el título de reproducción actual (Spotify, YouTube, etc.).
  * ⚠️ **Gotcha de Sesión 0:** esta API lee la sesión del usuario logueado. Un servicio NSSM corre en Sesión 0 sin contexto multimedia → devuelve vacío. Solución: ejecutar la parte multimedia como tarea del usuario (Task Scheduler con trigger de logon) o configurar el servicio para interactuar con el escritorio.
* **Despliegue:** servicio nativo de Windows con **NSSM** para arranque automático e invisible.

### 🔑 Patrón central: hilo de caché + SSE stream

Un **hilo en background** lee los sensores a ritmo fijo (cada ~2s) y actualiza un diccionario en memoria. La ruta SSE de Flask lee ese diccionario y empuja los datos al cliente. Las peticiones HTTP **nunca disparan lecturas de hardware directas**.

```
[Hilo sensor] → [dict caché en memoria] → [Flask SSE stream] → [EventSource en tablet]
```

**Por qué:** desacopla lectura de hardware y entrega al cliente. Sin importar cuántas tablets estén conectadas o si alguna pierde conexión, el hardware se lee a ritmo constante y controlado.

---

## 📊 Diccionario de Datos (Payload del Stream SSE)

Este es el paquete exacto de métricas que el servidor Flask empuja al cliente en cada evento SSE. Todos los campos deben estar presentes en cada emisión; usar `0.0` / `""` como fallback si una lectura falla, para no romper el frontend.

### 1. Sistema (CPU & RAM) — fuente: `psutil`

| Campo | Tipo | Descripción |
|---|---|---|
| `cpu_load` | `float` | Uso del procesador (%) |
| `ram_total` | `float` | RAM física total instalada (GB) |
| `ram_used` | `float` | RAM consumida actualmente (GB) |
| `ram_percent` | `float` | Ocupación de RAM (%) |

### 2. GPU (AMD Radeon RX 7800 XT) — fuente: `OpenHardwareMonitorLib.dll` vía `pythonnet`

| Campo | Tipo | Descripción |
|---|---|---|
| `gpu_usage` | `float` | Carga de trabajo de la GPU (%) |
| `gpu_temp` | `float` | Temperatura del chip gráfico (°C) |
| `fps` | `float` | Fotogramas por segundo — **simulado por ahora**, integración real pendiente |

### 3. Multimedia — fuente: `winsdk` (GSMTC)

| Campo | Tipo | Descripción |
|---|---|---|
| `media_status` | `str` | Estado: `"Reproduciendo"` / `"Pausado"` / `"Detenido"` |
| `media_title` | `str` | Título de la canción o ventana activa (ej. `"Artist - Song · YouTube"`) |

### Ejemplo de payload JSON por evento SSE

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

> **Nota `fps`:** el campo siempre se incluye en el payload para no cambiar la estructura del JSON cuando se implemente la lectura real. Por ahora se emite como `0.0`.

---

## 🗺️ Mapa de Ruta (Fases del Proyecto)

### ✅ Fase 1: Fundaciones y Entorno
* [x] Estructurar el proyecto (`src/server`, `src/sensors`, `web/`).
* [x] Servidor web base con Flask.
* [x] **PIVOTE ARQUITECTÓNICO:** migración de WSL2 a Windows nativo.

### 🟡 Fase 2: Sensores Base (CPU y Memoria) — REFACTOR PENDIENTE
* [x] Módulo `sensors.py` aislado.
* [ ] **Migrar CPU/RAM de PowerShell a `psutil`.** Eliminar llamadas `subprocess`.
* [ ] Implementar **hilo de caché en background**.
* [ ] Conectar caché con stream SSE de Flask, con `try-except` (fallback a `0.0`).

### 🟡 Fase 3: Integración GPU (En Progreso)
* [x] Open Hardware Monitor instalado y corriendo en background.
* [ ] Integrar `OpenHardwareMonitorLib.dll` vía `pythonnet`: objeto `Computer` → `GPUEnabled` → recorrer árbol de sensores.
* [ ] Extraer **uso (%)** y **temperatura** de la RX 7800 XT e inyectarlos en el caché.

### ⏳ Fase 4: Multimedia e Interfaz Visual Final
* [ ] **SSE endpoint:** ruta Flask que sirve `text/event-stream` con las métricas en JSON.
* [ ] **Frontend:** `index.html` + CSS oscuro, tarjetas estilizadas (UI gamer/tech), optimizado para 1280×800 landscape, actualización de DOM mínima.
* [ ] **JS:** `EventSource` con reconexión automática, actualización de nodos individuales.
* [ ] **Multimedia:** `winsdk` para título de reproducción actual (resolver gotcha Sesión 0).

### ⏳ Fase 5: Despliegue en Producción
* [ ] Limpiar código de pruebas y `print` innecesarios.
* [ ] Envolver con **`waitress`** en vez de `app.run()`.
* [ ] Registrar con **NSSM** como servicio silencioso.
* [ ] Resolver ejecución multimedia fuera de Sesión 0.

---

## 🛠️ Reglas de Desarrollo

1. **Hardware real:** leer sensores nativos, no entornos virtuales.
2. **Lecturas ligeras:** `psutil` para CPU/RAM, DLL nativa para GPU. Nada de PowerShell en cada poll.
3. **Caché siempre:** el stream SSE lee del diccionario en memoria, nunca directamente del hardware.
4. **Resiliencia:** toda función sensora lleva `try/except` y devuelve `0.0` para no tumbar el servidor.
5. **Frontend liviano:** sin librerías externas, DOM mínimo, sin animaciones pesadas. El cliente es hardware limitado.
6. **SSE sobre polling:** una conexión persistente es mejor que N peticiones por segundo para un MediaPad del 2013.
7. **Producción ≠ desarrollo:** `waitress` para servir, nunca el servidor de Flask.

---

## 📐 Datos del Hardware Objetivo

| Componente | Detalle |
|---|---|
| GPU | AMD Radeon RX 7800 XT |
| RAM | 32 GB |
| OS host | Windows (nativo, no VM) |
| Cliente | Huawei MediaPad 10, Android 4.1, Firefox 68.11.0 (Gecko) |
| Resolución cliente | 1280×800, 10.1", landscape |
