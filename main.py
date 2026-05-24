from src.server.app import app

def main():
    print("Iniciando Servidor de Panel de Telemetría...")
    print("Accesible en red local: http://<tu-ip-local>:8080")
    app.run(host="0.0.0.0", port=8080, debug=True)

if __name__ == "__main__":
    main()
