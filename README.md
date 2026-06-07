# KIRA Telemetry Panel

Panel web de telemetría en tiempo real para PC, monitoreable desde una tablet vía WiFi en red local. Muestra CPU, RAM, GPU, FPS y estado multimedia con una interfaz HUD estilo sci-fi oscuro.

---

## Hardware

| Componente | Detalle |
|---|---|
| Host | Windows 11 Pro |
| GPU | AMD Radeon RX 7800 XT |
| RAM | 32 GB DDR5 |
| Cliente | Huawei MediaPad 10 (2013), Android 4.1, Firefox 68.11, 1280×800 landscape |

El cliente es un dispositivo de 2013 con recursos limitados — toda decisión de arquitectura y frontend prioriza eficiencia sobre conveniencia.

---

## Arquitectura

```
[Hilo sensor cada ~2s]
        |
        v
[dict caché en memoria]  ←  sensor_cache en app.py
        |
        v
[Flask SSE /stream]  →  [EventSource en tablet]
```

Un hilo en background (`sensor-loop`) lee los sensores a ritmo fijo y actualiza un diccionario en memoria. La ruta `/stream` empuja JSON al cliente via Server-Sent Events. Las peticiones HTTP nunca disparan lecturas de hardware directas.

---

## Estructura del proyecto

```
telemetry-panel/
├── main.py                      # Entry point: arranca waitress (producción)
├── pyproject.toml               # Dependencias gestionadas con uv
├── avatar/                      # Imágenes PNG del avatar (transparente, rotación automática)
├── scripts/
│   ├── install_task.ps1         # Registra KIRA en Task Scheduler (logon, con multimedia)
│   └── uninstall_task.ps1       # Elimina la tarea
├── tools/
│   ├── bin/
│   │   └── gpu_sensor.exe       # Exe C# compilado — lee GPU via LibreHardwareMonitor
│   └── gpu_sensor/
│       ├── Program.cs           # Fuente del exe (imprime JSON a stdout)
│       └── gpu_sensor.csproj    # .NET 9, PublishSingleFile
├── src/
│   ├── server/
│   │   └── app.py               # Flask: hilo sensor, rutas /, /stream, /avatar/*
│   └── sensors/
│       └── sensors.py           # Lectura de hardware: CPU, RAM, GPU, FPS, multimedia
└── web/
    ├── templates/
    │   └── index.html           # HUD: estructura + JS vanilla (SSE, avatar, reloj)
    └── static/
        └── style.css            # Estilos NEURAL GRID oscuros optimizados para tablet
```

---

## Stack de dependencias

| Librería | Uso |
|---|---|
| `psutil` | CPU load y uso de RAM (nativo, sin PowerShell) |
| `Flask` | Servidor web + SSE stream |
| `waitress` | Servidor WSGI para producción |
| `winsdk` | GSMTC — estado multimedia del sistema (Windows 10+) |

**GPU:** exe C# separado (`tools/bin/gpu_sensor.exe`) usando `LibreHardwareMonitor` como NuGet. Python lo llama via `subprocess` en cada ciclo del sensor loop. No requiere pythonnet ni OHM instalado.

**FPS:** RTSS shared memory (`RTSSSharedMemoryV2`) via ctypes. Fallback automático a refresh rate del monitor (`GetDeviceCaps`) cuando no hay juego activo.

---

## Requisitos previos

- [uv](https://docs.astral.sh/uv/) — gestor de paquetes
- Python 3.12 (uv lo descarga automáticamente)
- [RTSS (RivaTuner Statistics Server)](https://www.guru3d.com/files-details/rtss-rivatuner-statistics-server-download.html) — necesario para lectura de FPS en juegos
- .NET 9 Runtime — para ejecutar `gpu_sensor.exe`

---

## Instalación

```powershell
git clone <url>
cd telemetry-panel
uv sync
```

`uv sync` lee `pyproject.toml` + `uv.lock` y reproduce el entorno exacto.

---

## Uso en desarrollo

```powershell
# Iniciar el servidor
uv run python main.py

# Probar sensores en forma aislada (sin Flask)
uv run python -m src.sensors.sensors
```

Acceder desde el navegador:
- **Local:** `http://localhost:7842`
- **Tablet (red local):** `http://<ip-del-pc>:7842`

---

## Despliegue en producción (Task Scheduler)

```powershell
# Ejecutar como Administrador
PowerShell -ExecutionPolicy Bypass -File scripts\install_task.ps1
```

Registra una tarea que arranca KIRA automáticamente al hacer login. Corre en la sesión del usuario (no Sesión 0), lo que permite acceso al contexto multimedia de Windows. Reinicio automático en caso de crash.

Para desinstalar:
```powershell
PowerShell -ExecutionPolicy Bypass -File scripts\uninstall_task.ps1
```

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
  "fps": 144.0,
  "fps_source": "game",
  "media_status": "Reproduciendo",
  "media_title": "Infected Mushroom - Converting Vegetarians · YouTube"
}
```

`fps_source` puede ser `"game"` (RTSS activo) o `"display"` (refresh rate del monitor como fallback). El frontend muestra "FPS" o "Hz" según este campo.

---

## Lectura de GPU

`gpu_sensor.exe` usa `LibreHardwareMonitor` para leer uso (%) y temperatura (°C) de la GPU. Python lo llama via subprocess y parsea el JSON de stdout:

```
{"gpu_usage": 81.0, "gpu_temp": 72.0}
```

Para recompilar el exe (requiere .NET 9 SDK):
```powershell
cd tools/gpu_sensor
dotnet publish -c Release -r win-x64 -o ../bin
```

---

## Avatar

La carpeta `avatar/` contiene imágenes PNG con fondo transparente que se muestran en la tarjeta NOW PLAYING. El servidor las sirve via `/avatar/<filename>` y `/avatar/list`. El frontend carga la lista dinámicamente — agregar o reemplazar imágenes en la carpeta no requiere tocar código, solo recargar la página.

Las imágenes rotan aleatoriamente cada 3 minutos con transición de fade.

---

## Multimedia

Usa `GlobalSystemMediaTransportControlsSessionManager` (GSMTC) de Windows a través de `winsdk`. Devuelve artista, título y estado (Reproduciendo / Pausado / Detenido).

Requiere correr en la sesión del usuario — el Task Scheduler con trigger de logon resuelve esto. Si corre como servicio Windows (Sesión 0), el multimedia estará vacío.

---

## Decisiones de diseño

- **SSE sobre polling:** un `EventSource` abierto es más eficiente que requests HTTP repetidos en hardware limitado.
- **Sin librerías JS externas:** vanilla JS puro — no jQuery, no React, no Chart.js.
- **DOM mínimo:** solo se actualizan los nodos que cambian, nunca se re-renderizan tarjetas enteras.
- **GPU via exe C#:** más liviano que mantener OHM corriendo; el exe lee, imprime y sale en < 1s.
- **Task Scheduler sobre NSSM:** NSSM corre en Sesión 0 y rompe el multimedia; Task Scheduler corre en sesión del usuario.
- **Fondo oscuro:** lectura continua y ahorro de batería.
