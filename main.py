import os
import subprocess
from src.server.app import app

def run_wsl_bridge():
    try:
        print("Configurando puente de red para WSL2...")
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "scripts", "puente_wsl.ps1"))
        result = subprocess.run(["wslpath", "-w", script_path], capture_output=True, text=True, check=True)
        win_path = result.stdout.strip()
        # Se ejecuta sin bloquear el hilo principal
        subprocess.Popen(["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", win_path])
    except Exception as e:
        print(f"Advertencia: No se pudo ejecutar el script puente automáticamente: {e}")

def main():
    # En modo debug, Flask se ejecuta dos veces (proceso principal y reloader).
    # Solo ejecutamos el puente en el primer arranque para evitar colisiones en PowerShell.
    if os.environ.get('WERKZEUG_RUN_MAIN') is None:
        run_wsl_bridge()
        
    print("Iniciando Servidor de Panel de Telemetría...")
    print("Accesible en red local: http://<tu-ip-local>:8080")
    app.run(host="0.0.0.0", port=8080, debug=True)

if __name__ == "__main__":
    main()
