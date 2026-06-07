# KIRA Telemetry Panel

Panel web de telemetría en tiempo real para PC, monitoreable desde una tablet vía WiFi en red local. Muestra CPU, RAM, GPU, FPS, estado multimedia y un visualizador de audio reactivo con interfaz HUD estilo sci-fi oscuro.

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
[Hilo sensor cada ~2s]              [Hilo audio cada ~100ms]
        |                                      |
        v                                      v
[dict caché en memoria]             [buffer espectro FFT]
        |                                      |
        v                                      v
[Flask SSE /stream]  ──────────────  [Flask SSE /stream/audio]
        |                                      |
        └──────────────┬────────────────────────┘
                       v
              [EventSource en tablet]
```

Un hilo `sensor-loop` lee hardware cada ~2 s. Un hilo separado captura el espectro de audio del sistema cada ~100 ms vía WASAPI loopback. Ambos streams se sirven como SSE independientes. Las peticiones HTTP nunca disparan lecturas de hardware directas.

---

## Estructura del proyecto

```
telemetry-panel/
├── main.py                      # Entry point: arranca waitress (producción)
├── pyproject.toml               # Dependencias gestionadas con uv
├── avatar/                      # PNGs del avatar (fondo transparente, rotación automática)
├── scripts/
│   ├── install_task.ps1         # Registra KIRA en Task Scheduler (logon, con multimedia)
│   └── uninstall_task.ps1       # Elimina la tarea del scheduler
├── tools/
│   ├── bin/
│   │   └── gpu_sensor.exe       # Exe C# compilado — lee GPU via LibreHardwareMonitor
│   └── gpu_sensor/
│       ├── Program.cs           # Fuente del exe (imprime JSON a stdout)
│       └── gpu_sensor.csproj    # .NET 9, PublishSingleFile
├── src/
│   ├── server/
│   │   └── app.py               # Flask: rutas /, /stream, /stream/audio, /avatar/*, /media/*
│   └── sensors/
│       ├── sensors.py           # CPU, RAM, GPU, FPS (RTSS), multimedia (GSMTC)
│       └── audio.py             # Espectro de audio vía WASAPI loopback (sounddevice + numpy)
└── web/
    ├── templates/
    │   └── index.html           # HUD: estructura, JS vanilla (SSE, Jarvis, avatar, reloj)
    └── static/
        └── style.css            # Estilos NEURAL GRID oscuros optimizados para tablet
```

---

## Stack de dependencias

| Librería | Uso |
|---|---|
| `psutil` | CPU load y uso de RAM |
| `Flask` | Servidor web + SSE streams |
| `waitress` | Servidor WSGI para producción |
| `winsdk` | GSMTC — estado y control multimedia de Windows |
| `sounddevice` | Captura de audio loopback vía WASAPI |
| `numpy` | FFT para el espectro de audio |

**GPU:** exe C# separado (`tools/bin/gpu_sensor.exe`) usando `LibreHardwareMonitor` como NuGet. Python lo llama via `subprocess` en cada ciclo. No requiere pythonnet ni OHM instalado.

**FPS:** RTSS shared memory (`RTSSSharedMemoryV2`) via ctypes. Fallback a refresh rate del monitor (`GetDeviceCaps`) cuando no hay juego activo.

---

## Requisitos previos

- [uv](https://docs.astral.sh/uv/) — gestor de paquetes
- Python 3.12 (uv lo descarga automáticamente)
- [RTSS (RivaTuner Statistics Server)](https://www.guru3d.com/files-details/rtss-rivatuner-statistics-server-download.html) — necesario para FPS en juegos
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

Registra una tarea que arranca KIRA automáticamente al hacer login. Corre en la sesión del usuario (no Sesión 0), lo que permite acceso al contexto multimedia de Windows (GSMTC) y al audio loopback (WASAPI). Reinicio automático en caso de crash.

Para desinstalar:
```powershell
PowerShell -ExecutionPolicy Bypass -File scripts\uninstall_task.ps1
```

---

## Payload SSE — `/stream`

Cada ~2 segundos:

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

`fps_source`: `"game"` (RTSS activo) o `"display"` (refresh rate del monitor). El frontend muestra "FPS" o "Hz" según este campo.

## Payload SSE — `/stream/audio`

Cada ~100 ms — 8 bandas de frecuencia (0–100 por banda):

```json
[0.0, 42.3, 78.1, 55.0, 30.2, 18.4, 8.7, 3.1]
```

El frontend usa estas bandas para animar el visualizador Jarvis (arc-reactor holográfico) en la tarjeta NOW PLAYING.

---

## Control multimedia — `/media/<action>`

Endpoint POST para controlar la reproducción vía GSMTC:

| Ruta | Acción |
|---|---|
| `POST /media/prev` | Pista anterior |
| `POST /media/playpause` | Play / Pausa |
| `POST /media/next` | Pista siguiente |

Devuelve `204 No Content`. Los botones del HUD llaman a estos endpoints directamente con `fetch`.

---

## Visualizador Jarvis

Canvas 2D en el card NOW PLAYING. Dibuja un arc-reactor holográfico reactivo al audio:

- **Core:** círculo central que pulsa con el bajo
- **Anillos:** 3 arcos concéntricos con gap que se cierra en los beats
- **Partículas:** 28 puntos en órbita cuya velocidad aumenta con los agudos
- **Beat detection:** umbral adaptativo (`avgBass * 1.30`) — detecta spikes relativos, no nivel absoluto

Parámetros ajustables en `index.html` (objeto `JARVIS`):

```javascript
var JARVIS = {
    coreSpeed:     1.0,  // velocidad rotación arc central  (0.5–3.0)
    particleCount: 28,   // cantidad de partículas          (10–80)
    particleSpeed: 1.0,  // velocidad base de partículas    (0.3–2.5)
    fps:           20,   // cap de frames del canvas        (15–60)
};
```

---

## Avatar

La carpeta `avatar/` contiene PNGs con fondo transparente. El servidor los sirve via `/avatar/<filename>` y `/avatar/list`. El frontend carga la lista dinámicamente — agregar imágenes no requiere tocar código, solo recargar la página.

Rotan aleatoriamente cada 3 minutos con transición de fade.

---

## Decisiones de diseño

- **SSE sobre polling:** un `EventSource` abierto es más eficiente que requests HTTP repetidos en hardware limitado.
- **Sin librerías JS externas:** vanilla JS puro — no jQuery, no React, no Chart.js.
- **DOM mínimo:** solo se actualizan los nodos que cambian, nunca se re-renderizan tarjetas enteras.
- **GPU via exe C#:** más liviano que mantener OHM corriendo; el exe lee, imprime y sale en < 1s.
- **Task Scheduler sobre NSSM:** NSSM corre en Sesión 0 y rompe multimedia y audio loopback; Task Scheduler corre en sesión del usuario.
- **20 fps en el canvas Jarvis:** suficiente para percibir reactividad al audio sin saturar la CPU del MediaPad.
- **Fondo oscuro:** lectura continua y ahorro de batería en OLED/LCD.
