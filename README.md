# JARVIS Telemetry Panel

Panel web de telemetría en tiempo real para PC, diseñado para ser monitoreado desde una tablet vía WiFi en red local. Muestra CPU, RAM, GPU y estado multimedia con una interfaz estilo HUD.

---

## Contexto del hardware

| Componente | Detalle |
|---|---|
| Host | Windows 11 Pro |
| GPU | AMD Radeon RX 7800 XT |
| RAM | 32 GB DDR5 |
| Cliente | Huawei MediaPad 10 (2013), Android 4.1, Firefox 68.11 |

El cliente es un dispositivo de 2013 con recursos limitados — toda decisión de arquitectura y frontend prioriza eficiencia sobre conveniencia.

---

## Arquitectura

```
[Hilo sensor cada ~2s]
        |
        v
[dict caché en memoria]  <-- sensor_cache en app.py
        |
        v
[Flask SSE /stream]  -->  [EventSource en tablet]
```

Un hilo en background (`sensor-loop`) lee los sensores a ritmo fijo y actualiza un diccionario en memoria. La ruta `/stream` de Flask lee ese diccionario y empuja JSON al cliente via Server-Sent Events. Las peticiones HTTP nunca disparan lecturas de hardware directas.

---

## Estructura del proyecto

```
telemetry-panel/
├── main.py                    # Entry point: arranca Flask en modo dev
├── src/
│   ├── server/
│   │   └── app.py             # Flask app, hilo sensor, rutas / y /stream
│   └── sensors/
│       └── sensors.py         # Funciones de lectura de hardware
└── web/
    ├── templates/
    │   └── index.html         # HUD: HTML + JS vanilla con EventSource
    └── static/
        └── style.css          # Estilos oscuros optimizados para tablet
```

---

## Stack de dependencias

| Librería | Uso |
|---|---|
| `psutil` | CPU load y uso de RAM (nativo, sin PowerShell) |
| `Flask` | Servidor web + SSE stream |
| `waitress` | Servidor WSGI para producción (reemplaza `app.run()`) |
| `pythonnet` (`clr`) | Acceso a `OpenHardwareMonitorLib.dll` para GPU temp |
| `winsdk` | GSMTC — estado multimedia del sistema (Windows 10+) |

---

## Requisitos previos

- [uv](https://docs.astral.sh/uv/) (gestor de paquetes y entornos virtuales)
- Python 3.12 (uv lo descarga automáticamente si no está instalado)
- [Open Hardware Monitor](https://openhardwaremonitor.org/) instalado (para temperatura de GPU)
- `pythonnet` requiere .NET Framework instalado en el sistema

---

## Instalación

```powershell
# Clonar el repositorio
git clone <url>
cd telemetry-panel

# Instalar dependencias y crear el entorno virtual (.venv) en un solo paso
uv sync
```

`uv sync` lee `pyproject.toml` + `uv.lock` y reproduce el entorno exacto. No hace falta crear el `.venv` ni correr `pip install` a mano.

---

## Uso

```powershell
# Iniciar el servidor de desarrollo
uv run python main.py

# Probar sensores en forma aislada (sin Flask)
uv run python -m src.sensors.sensors
```

`uv run` usa automáticamente el entorno virtual del proyecto sin necesidad de activarlo manualmente.

Acceder desde el navegador:
- **Local:** `http://localhost:8090`
- **Tablet (red local):** `http://<ip-del-pc>:8090`

---

## Payload SSE

Cada ~2 segundos el servidor emite un JSON con esta estructura fija:

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

`fps` siempre es `0.0` hasta que se implemente la lectura real. El campo existe para no romper la estructura del JSON.

---

## Lectura de GPU

El módulo `sensors.py` intenta dos métodos en orden:

1. **`OpenHardwareMonitorLib.dll` vía `pythonnet`** — devuelve uso (%) y temperatura. Requiere que OHM esté instalado en el sistema.
2. **Fallback WMI via PowerShell** — devuelve solo uso (%), sin temperatura. Se usa si la DLL no se encuentra.

Para que OHM funcione se puede configurar la ruta de la DLL con la variable de entorno `OHM_DLL_PATH`, o dejarla en la ubicación por defecto (`C:\Program Files\OpenHardwareMonitor\`).

---

## Multimedia

Usa la API `GlobalSystemMediaTransportControlsSessionManager` (GSMTC) de Windows a través de `winsdk`. Devuelve artista, título y estado de reproducción (Reproduciendo / Pausado / Detenido).

**Limitación conocida:** si el servidor corre como servicio Windows (Sesión 0), el contexto multimedia estará vacío. La solución planeada es lanzar la parte multimedia via Task Scheduler con trigger de logon en lugar de NSSM.

---

## Roadmap

| Fase | Estado | Descripción |
|---|---|---|
| 1 — Fundaciones | Completa | Estructura, Flask base, migración WSL2 → Windows nativo |
| 2 — Sensores base | Completa | `psutil` para CPU/RAM, hilo de caché, SSE conectado |
| 3 — GPU | Parcial | OHM integrado; falta validar temperatura en hardware real |
| 4 — Multimedia e interfaz | Pendiente | HUD final, CSS oscuro optimizado, EventSource con reconexión |
| 5 — Producción | Pendiente | `waitress` + NSSM como servicio, resolver Sesión 0 |

---

## Decisiones de diseño relevantes

- **SSE sobre polling:** un `EventSource` abierto es más eficiente que un request HTTP por segundo en hardware limitado.
- **Sin librerías JS externas:** vanilla JS puro — no jQuery, no React, no Chart.js.
- **DOM mínimo:** solo se actualizan los nodos que cambian, nunca se re-renderizan tarjetas enteras.
- **Sin animaciones CSS pesadas:** sin `keyframes`, sin `blur`, sin `box-shadow` excesivo — la tablet no los aguanta.
- **Fondo oscuro:** lectura continua y ahorro de batería en pantalla AMOLED/LCD.
