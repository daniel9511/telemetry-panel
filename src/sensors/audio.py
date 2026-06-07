"""
audio.py — Captura el audio del sistema y calcula el espectro de frecuencias.

Flujo completo:
  [WASAPI loopback: lo que suena en los speakers]
        → chunk de 2048 muestras (~43ms)
        → FFT: dominio tiempo → dominio frecuencia
        → 24 bandas log-espaciadas (como el oído humano)
        → suavizado attack/decay
        → guardado en variables globales
        → Flask lee esas variables para el SSE de audio

Selección de dispositivo:
  Al arrancar (y cuando hay silencio prolongado), escanea todos los
  loopback disponibles y usa el que tenga más señal en ese momento.
  Esto cubre setups con SteelSeries Sonar u otros routers de audio
  virtual donde el "default speaker" puede no ser el canal activo.
"""

import threading
import time

import numpy as np
import soundcard as sc

# ── Constantes ──────────────────────────────────────────────
SAMPLE_RATE     = 48000   # Hz estándar de Windows
CHUNK           = 2048    # muestras por bloque (~43ms de audio por iteración)
N_BANDS         = 24      # bandas de frecuencia en el visualizador
_MIN_DB         = -70.0   # dBFS — silencio
_MAX_DB         =   0.0   # dBFS — pico máximo digital
# Para un rfft con ventana Hanning: pico teórico = amplitud * CHUNK/4
# Dividir fft por _FFT_REF normaliza a escala 0-1 → dBFS estándar
_FFT_REF        = CHUNK / 4
_RESCAN_CHUNKS  = 200     # chunks de silencio antes de re-escanear (~8.5s)

# ── Estado global ────────────────────────────────────────────
_spectrum: list[float] = [0.0] * N_BANDS
_level:    float       = 0.0

# ── Pre-cómputo (se hace una sola vez al importar) ───────────
_freqs      = np.fft.rfftfreq(CHUNK, 1.0 / SAMPLE_RATE)
_band_edges = np.logspace(np.log10(30.0), np.log10(16000.0), N_BANDS + 1)
_ventana    = np.hanning(CHUNK)


def _best_loopback_name() -> str:
    """
    Escanea todos los dispositivos loopback disponibles (0.5s cada uno),
    devuelve el nombre del que tenga mayor RMS en ese momento.

    Necesario cuando hay routers de audio virtual (SteelSeries Sonar, VoiceMeeter)
    donde el default speaker puede no ser el canal con señal activa.
    """
    best_name = sc.default_speaker().name
    best_rms  = -1.0

    for mic in sc.all_microphones(include_loopback=True):
        try:
            with mic.recorder(samplerate=SAMPLE_RATE, channels=2) as r:
                data = r.record(numframes=2048)
                rms  = float(np.sqrt(np.mean(data ** 2)))
                if rms > best_rms:
                    best_rms  = rms
                    best_name = mic.name
        except Exception:
            pass

    print(f"[audio] Dispositivo seleccionado: {best_name} (RMS={best_rms:.5f})")
    return best_name


def _capture_loop() -> None:
    """
    Hilo de captura principal. Bucle externo: selecciona dispositivo.
    Bucle interno: captura y procesa hasta detectar silencio prolongado.
    """
    global _spectrum, _level

    while True:
        dev_name = _best_loopback_name()

        try:
            prev          = [0.0] * N_BANDS
            silent_chunks = 0

            with sc.get_microphone(
                dev_name, include_loopback=True
            ).recorder(samplerate=SAMPLE_RATE, channels=2) as mic:

                while True:
                    # 1. Captura un chunk
                    data = mic.record(numframes=CHUNK)

                    # 2. Estéreo → mono
                    mono = data.mean(axis=1)

                    # 3. FFT — normalizado a escala 0-1 para señal de amplitud 1.0
                    fft = np.abs(np.fft.rfft(mono * _ventana)) / _FFT_REF

                    # 4. Magnitud → dBFS → normaliza 0-100
                    mag_db   = 20.0 * np.log10(fft + 1e-6)
                    mag_norm = np.clip(
                        (mag_db - _MIN_DB) / (_MAX_DB - _MIN_DB) * 100.0,
                        0.0, 100.0
                    )

                    # 5. Agrupa en N_BANDS bandas log-espaciadas con suavizado
                    bands: list[float] = []
                    for i in range(N_BANDS):
                        lo   = _band_edges[i]
                        hi   = _band_edges[i + 1]
                        mask = (_freqs >= lo) & (_freqs < hi)
                        val  = float(mag_norm[mask].mean()) if mask.any() else 0.0

                        if val > prev[i]:
                            prev[i] = prev[i] * 0.15 + val * 0.85
                        else:
                            prev[i] = prev[i] * 0.72 + val * 0.28
                        bands.append(round(prev[i], 1))

                    lv = round(float(np.mean(bands)), 1)
                    _spectrum = bands
                    _level    = lv

                    # 6. Re-escanea si hay silencio prolongado
                    if lv < 0.5:
                        silent_chunks += 1
                    else:
                        silent_chunks = 0

                    if silent_chunks >= _RESCAN_CHUNKS:
                        print("[audio] Silencio prolongado — buscando dispositivo activo")
                        break  # sale al bucle externo, re-escanea

        except Exception as e:
            print(f"[audio] Error con '{dev_name}': {e} — reintentando en 1s")
            _spectrum = [0.0] * N_BANDS
            _level    = 0.0
            time.sleep(1)


def start_audio_thread() -> None:
    threading.Thread(
        target=_capture_loop, daemon=True, name="audio-loop"
    ).start()


def get_spectrum() -> dict:
    return {"bands": _spectrum, "level": _level}


if __name__ == "__main__":
    """Prueba aislada: uv run python -m src.sensors.audio"""
    start_audio_thread()
    print("Capturando audio del sistema... tocá algo en la PC")
    print("Ctrl+C para salir\n")
    while True:
        d = get_spectrum()
        bar = "".join(
            "█" * int(v / 10) + "░" * (10 - int(v / 10))
            for v in d["bands"]
        )
        print(f"\r[{bar}] {d['level']:4.0f}%", end="", flush=True)
        time.sleep(0.066)
