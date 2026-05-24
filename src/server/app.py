import os
from flask import Flask, render_template

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
    # Estos son datos estáticos temporales (MVP). 
    # Luego los obtendremos leyendo los sensores reales.
    datos_telemetria = {
        'fps': 120,
        'cpu_load': 45.2,
        'ram_used': 16.5,
        'media_title': 'Ejemplo - YouTube'
    }
    return render_template('index.html', datos=datos_telemetria)
