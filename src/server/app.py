import os
from flask import Flask, render_template
from src.sensors.sensors import get_cpu_load, get_ram_usage

# Calcular la ruta a la carpeta web (dos niveles arriba de app.py)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WEB_DIR = os.path.join(BASE_DIR, 'web')

app = Flask(
    __name__,
    template_folder=os.path.join(WEB_DIR, 'templates'),
    static_folder=os.path.join(WEB_DIR, 'static')
)

@app.route('/')
def index():
    # Obtener las métricas reales del host de Windows
    ram_info = get_ram_usage()
    
    # Empaquetar los datos de telemetría
    datos_telemetria = {
        'fps': 120,  # Temporal (Fase AMD pendiente)
        'cpu_load': get_cpu_load(),
        'ram_used': ram_info.get('used_gb', 0.0),
        'media_title': 'Ejemplo - YouTube'  # Temporal (Fase Multimedia pendiente)
    }
    return render_template('index.html', datos=datos_telemetria)
