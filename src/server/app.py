import json
import os
import threading
import time

from flask import Flask, Response, render_template

from src.sensors.sensors import (
    get_cpu_load,
    get_gpu_metrics,
    get_media_info,
    get_ram_usage,
    init_media_loop,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WEB_DIR = os.path.join(BASE_DIR, "web")

app = Flask(
    __name__,
    template_folder=os.path.join(WEB_DIR, "templates"),
    static_folder=os.path.join(WEB_DIR, "static"),
)

sensor_cache: dict = {
    "cpu_load": 0.0,
    "ram_total": 0.0,
    "ram_used": 0.0,
    "ram_percent": 0.0,
    "gpu_usage": 0.0,
    "gpu_temp": 0.0,
    "fps": 0.0,
    "media_status": "",
    "media_title": "",
}


def _sensor_loop():
    init_media_loop()
    while True:
        try:
            ram = get_ram_usage()
            gpu = get_gpu_metrics()
            media = get_media_info()
            sensor_cache.update({
                "cpu_load": get_cpu_load(),
                "ram_total": ram["total_gb"],
                "ram_used": ram["used_gb"],
                "ram_percent": ram["ram_percent"],
                "gpu_usage": gpu["gpu_usage"],
                "gpu_temp": gpu["gpu_temp"],
                "media_status": media["media_status"],
                "media_title": media["media_title"],
            })
        except Exception as e:
            print(f"Error en sensor_loop: {e}")
        time.sleep(2)


threading.Thread(target=_sensor_loop, daemon=True, name="sensor-loop").start()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/stream")
def stream():
    def generate():
        try:
            while True:
                yield f"data: {json.dumps(sensor_cache)}\n\n"
                time.sleep(2)
        except GeneratorExit:
            pass

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
