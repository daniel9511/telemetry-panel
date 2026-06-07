from waitress import serve

from src.server.app import app

if __name__ == "__main__":
    print("KIRA Telemetry Panel iniciando...")
    print("Panel disponible en: http://localhost:8090")
    print("Red local:           http://<tu-ip>:8090")
    serve(app, host="0.0.0.0", port=8090, threads=4)
