import asyncio
import os
import subprocess
import sys

import psutil

# --- OHM: se intenta cargar UNA vez al importar el módulo ---
_ohm_available = False
_computer = None


def _init_ohm():
    global _ohm_available, _computer

    dll_path = os.environ.get("OHM_DLL_PATH", "")

    if not dll_path:
        candidates = [
            r"C:\Program Files\OpenHardwareMonitor\OpenHardwareMonitorLib.dll",
            r"C:\OpenHardwareMonitor\OpenHardwareMonitorLib.dll",
            r"C:\Program Files (x86)\OpenHardwareMonitor\OpenHardwareMonitorLib.dll",
        ]
        for path in candidates:
            if os.path.exists(path):
                dll_path = path
                break

    if not dll_path:
        print("OHM DLL no encontrada. GPU temp = 0.0 (solo uso via WMI).")
        return

    try:
        dll_dir = os.path.dirname(dll_path)
        if dll_dir not in sys.path:
            sys.path.append(dll_dir)
        import clr
        clr.AddReference("OpenHardwareMonitorLib")
        from OpenHardwareMonitor.Hardware import Computer
        _computer = Computer()
        _computer.GPUEnabled = True
        _computer.Open()
        _ohm_available = True
        print(f"OHM cargado: {dll_path}")
    except Exception as e:
        print(f"OHM no disponible ({e}). GPU temp = 0.0.")


_init_ohm()

# --- Event loop para winsdk (se inicializa en el hilo sensor) ---
_media_loop: asyncio.AbstractEventLoop | None = None


def init_media_loop():
    global _media_loop
    _media_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_media_loop)


# --- CPU ---

def get_cpu_load() -> float:
    try:
        return psutil.cpu_percent(interval=None)
    except Exception:
        return 0.0


# --- RAM ---

def get_ram_usage() -> dict:
    try:
        m = psutil.virtual_memory()
        return {
            "total_gb": round(m.total / (1024 ** 3), 1),
            "used_gb": round(m.used / (1024 ** 3), 1),
            "ram_percent": round(m.percent, 1),
        }
    except Exception:
        return {"total_gb": 0.0, "used_gb": 0.0, "ram_percent": 0.0}


# --- GPU ---

def _get_gpu_via_ohm() -> dict:
    metrics = {"gpu_usage": 0.0, "gpu_temp": 0.0}
    try:
        from OpenHardwareMonitor.Hardware import SensorType
        for hw in _computer.Hardware:
            if "gpu" not in hw.Name.lower():
                continue
            hw.Update()
            for sensor in hw.Sensors:
                try:
                    if sensor.Value is None:
                        continue
                    val = float(sensor.Value)
                    if sensor.SensorType == SensorType.Load:
                        metrics["gpu_usage"] = round(val, 1)
                    elif sensor.SensorType == SensorType.Temperature:
                        metrics["gpu_temp"] = round(val, 1)
                except Exception:
                    continue
    except Exception as e:
        print(f"Error leyendo OHM: {e}")
    return metrics


def _get_gpu_via_wmi() -> dict:
    metrics = {"gpu_usage": 0.0, "gpu_temp": 0.0}
    try:
        cmd = [
            "powershell.exe", "-NoProfile", "-Command",
            "$g = Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine | "
            "Measure-Object -Property UtilizationPercentage -Sum; "
            "if ($g.Sum) { Write-Output $g.Sum } else { Write-Output 0 }",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=5)
        val = result.stdout.strip().replace(",", ".")
        if val:
            metrics["gpu_usage"] = round(min(float(val), 100.0), 1)
    except Exception as e:
        print(f"Error obteniendo GPU via WMI: {e}")
    return metrics


def get_gpu_metrics() -> dict:
    if _ohm_available:
        return _get_gpu_via_ohm()
    return _get_gpu_via_wmi()


# --- Multimedia ---

async def _get_media_async() -> dict:
    from winsdk.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as GSMTC,
    )
    manager = await GSMTC.request_async()
    session = manager.get_current_session()
    if not session:
        return {"media_status": "", "media_title": ""}

    info = await session.try_get_media_properties_async()
    playback = session.get_playback_info()
    status_val = int(playback.playback_status)

    status_map = {4: "Reproduciendo", 5: "Pausado", 2: "Detenido"}
    status = status_map.get(status_val, "")

    title = info.title or ""
    artist = info.artist or ""
    display = f"{artist} · {title}" if artist and title else (title or artist)

    return {"media_status": status, "media_title": display}


def get_media_info() -> dict:
    if _media_loop is None:
        return {"media_status": "", "media_title": ""}
    try:
        return _media_loop.run_until_complete(_get_media_async())
    except Exception as e:
        print(f"Error obteniendo multimedia: {e}")
        return {"media_status": "", "media_title": ""}


# --- Test directo del módulo ---

if __name__ == "__main__":
    print("--- Pruebas de sensores ---")
    print(f"CPU: {get_cpu_load()} %")

    ram = get_ram_usage()
    print(f"RAM Total:  {ram['total_gb']} GB")
    print(f"RAM Usada:  {ram['used_gb']} GB")
    print(f"RAM %:      {ram['ram_percent']} %")

    gpu = get_gpu_metrics()
    print(f"GPU Uso:    {gpu['gpu_usage']} %")
    print(f"GPU Temp:   {gpu['gpu_temp']} °C")

    # Multimedia requiere event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    _media_loop = loop
    media = get_media_info()
    print(f"Media:      {media['media_status']} — {media['media_title']}")
