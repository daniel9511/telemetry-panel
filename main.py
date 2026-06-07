from src.server.app import app

if __name__ == "__main__":
    print("Iniciando Panel de Telemetría...")
    print("Accesible en red local: http://<tu-ip-local>:8090")
    app.run(host="0.0.0.0", port=8090, debug=True, threaded=True)
