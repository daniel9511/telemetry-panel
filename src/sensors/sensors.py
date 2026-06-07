import asyncio
import ctypes
import json
import os
import subprocess
import threading

import psutil

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_GPU_EXE = os.path.join(_PROJECT_ROOT, "tools", "bin", "gpu_sensor.exe")

# --- Event loop para winsdk (se inicializa en el hilo sensor) ---
_media_loop: asyncio.AbstractEventLoop | None = None
_media_lock = threading.Lock()


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

def get_gpu_metrics() -> dict:
    metrics = {"gpu_usage": 0.0, "gpu_temp": 0.0}
    try:
        result = subprocess.run(
            [_GPU_EXE],
            capture_output=True, text=True, timeout=5,
        )
        data = json.loads(result.stdout.strip())
        metrics["gpu_usage"] = round(min(float(data.get("gpu_usage", 0.0)), 100.0), 1)
        metrics["gpu_temp"] = round(float(data.get("gpu_temp", 0.0)), 1)
    except Exception as e:
        print(f"Error obteniendo GPU: {e}")
    return metrics


# --- FPS via RTSS shared memory + refresh rate de monitor ---

def _dword_at(ptr: int, offset: int) -> int:
    return ctypes.c_uint32.from_address(ptr + offset).value


def _rtss_fps() -> float:
    k32 = ctypes.windll.kernel32
    k32.OpenFileMappingW.restype = ctypes.c_void_p
    k32.MapViewOfFile.restype    = ctypes.c_void_p

    handle = k32.OpenFileMappingW(0x0004, False, "RTSSSharedMemoryV2")
    if not handle:
        return 0.0

    ptr = k32.MapViewOfFile(handle, 0x0004, 0, 0, 0)
    if not ptr:
        k32.CloseHandle(handle)
        return 0.0

    try:
        if _dword_at(ptr, 0) != 0x52545353:
            return 0.0

        version        = _dword_at(ptr, 4)
        app_entry_size = _dword_at(ptr, 8)
        app_arr_offset = _dword_at(ptr, 12)
        app_arr_count  = _dword_at(ptr, 16)

        if app_entry_size == 0 or app_arr_count == 0:
            return 0.0

        target = None
        if version >= 0x00020010:
            idx = _dword_at(ptr, 64)
            if idx < app_arr_count:
                target = idx

        if target is None:
            best_t1 = 0
            for i in range(app_arr_count):
                base = app_arr_offset + i * app_entry_size
                t1 = _dword_at(ptr, base + 272)
                fr = _dword_at(ptr, base + 276)
                if fr > 0 and t1 > best_t1:
                    best_t1 = t1
                    target = i

        if target is None:
            return 0.0

        base       = app_arr_offset + target * app_entry_size
        frame_time = _dword_at(ptr, base + 280)
        time0      = _dword_at(ptr, base + 268)
        time1      = _dword_at(ptr, base + 272)
        frames     = _dword_at(ptr, base + 276)

        if frame_time > 0:
            return round(1_000_000.0 / frame_time, 1)
        if time1 > time0 and frames > 0:
            return round(1000.0 * frames / (time1 - time0), 1)
        return 0.0

    finally:
        k32.UnmapViewOfFile(ctypes.c_void_p(ptr))
        k32.CloseHandle(handle)


def _monitor_refresh_rate() -> float:
    try:
        VREFRESH = 116
        user32 = ctypes.windll.user32
        gdi32  = ctypes.windll.gdi32
        hdc = user32.GetDC(None)
        if hdc:
            rate = gdi32.GetDeviceCaps(hdc, VREFRESH)
            user32.ReleaseDC(None, hdc)
            return float(rate) if rate > 0 else 60.0
        return 60.0
    except Exception:
        return 60.0


def get_fps() -> tuple[float, str]:
    """Devuelve (fps, fuente) donde fuente es 'game' o 'display'."""
    try:
        fps = _rtss_fps()
        if fps > 0:
            return fps, "game"
    except Exception as e:
        print(f"Error leyendo RTSS: {e}")
    return _monitor_refresh_rate(), "display"


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
    with _media_lock:
        try:
            return _media_loop.run_until_complete(_get_media_async())
        except Exception as e:
            print(f"Error obteniendo multimedia: {e}")
            return {"media_status": "", "media_title": ""}


async def _media_command_async(action: str) -> None:
    from winsdk.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as GSMTC,
    )
    manager = await GSMTC.request_async()
    session = manager.get_current_session()
    if not session:
        return
    if action == "prev":
        await session.try_skip_previous_async()
    elif action == "next":
        await session.try_skip_next_async()
    elif action == "playpause":
        await session.try_toggle_play_pause_async()


def media_command(action: str) -> bool:
    if _media_loop is None or action not in ("prev", "next", "playpause"):
        return False
    with _media_lock:
        try:
            _media_loop.run_until_complete(_media_command_async(action))
            return True
        except Exception as e:
            print(f"Error en media_command({action}): {e}")
            return False


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
    fps_val, fps_src = get_fps()
    print(f"FPS:        {fps_val} ({fps_src})")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    _media_loop = loop
    media = get_media_info()
    print(f"Media:      {media['media_status']} — {media['media_title']}")
