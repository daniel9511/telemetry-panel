from waitress import serve

from src.server.app import app

if __name__ == "__main__":
    print("KIRA Telemetry Panel iniciando...")
    print("Panel disponible en: http://localhost:7842")
    print("Red local:           http://<tu-ip>:7842")
    serve(app, host="0.0.0.0", port=7842, threads=4)
