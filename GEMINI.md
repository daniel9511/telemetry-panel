# Documento de Planeación: Panel de Telemetría Local para Huawei MediaPad 10 Link

## 1. Resumen Ejecutivo

Este documento establece las especificaciones técnicas y el diseño de arquitectura para construir un panel de monitoreo de hardware personalizado y local. El sistema utilizará una tableta antigua Huawei MediaPad 10 Link (con recursos de hardware limitados y versión de Android obsoleta) exclusivamente como un visor pasivo (cliente web). Toda la lógica de recolección de telemetría, procesamiento y despacho de datos se ejecutará en segundo plano dentro del PC principal (servidor) con arquitectura AMD, garantizando un impacto mínimo en el rendimiento del sistema operativo y los videojuegos.

## 2. Objetivos del Proyecto

- **Reutilización de Hardware Obsoleto:** Dar una segunda vida a la tableta MediaPad 10 Link evitando la saturación de su memoria RAM mediante un esquema de consumo web estático.

- **Precisión Métricas AMD:** Capturar de forma nativa los fotogramas por segundo (FPS) y el tiempo de cuadro (Frametime) procesados bajo controladores con tecnologías activas de FSR (FidelityFX Super Resolution) y AFMF (AMD Fluid Motion Frames).

- **Monitoreo de Infraestructura y Multimedia:** Supervisar el estado de red local, almacenamiento físico, telemetría térmica del procesador y control del reproductor multimedia para YouTube Premium.

## 3. Arquitectura del Sistema

El diseño adopta un patrón Cliente-Servidor ligero corriendo enteramente sobre la red local (LAN):

| Capa | Tecnología / Origen | Función Principal |
|------|---------------------|-------------------|
| **Servidor (Backend)** | Python + Flask o FastAPI | Orquestador central. Expone un servicio HTTP local en el puerto 8080. Recopila los datos de los sensores del sistema cada 3 segundos. |
| **Telemetría Core & Gráficos** | Logs Nativos de AMD Adrenalin (CSV) | Lectura en tiempo real del buffer del archivo generado por el driver de AMD (Activación por atajo de teclado `Ctrl + Shift + L`). El script lee la última línea del archivo para evitar lecturas pesadas. |
| **Métricas de Sistema y Red** | Librería psutil (Python) | Mide el uso de CPU (%), consumo de RAM (GB), y calcula el ancho de banda de red local (Bytes enviados/recibidos) mediante diferencias temporales. |
| **Telemetría Térmica** | LibreHardwareMonitor (WMI / API) | Consulta las temperaturas de los núcleos del CPU y de las unidades de almacenamiento físico (SSD/HDD) a través de Windows Management Instrumentation. |
| **Capa Multimedia** | Windows Media Control API | Extracción de metadatos globales de audio en Windows para identificar la pista actual reproduciéndose desde YouTube Premium (Navegador o App). |
| **Cliente (Visualización)** | HTML5 Estático + CSS Base (MediaPad 10) | Renderizado minimalista en la tableta. Utiliza la directiva de cabecera HTML `<meta http-equiv="refresh" content="3">` para auto-actualizarse de manera pasiva sin inyectar JavaScript complejo ni WebSockets. |

## 4. Especificación de Métricas a Incluir

### Columna 1: Rendimiento y Gráficos (Módulo AMD Nativo)

- **FPS Reales:** Fotogramas por segundo precisos calculados post-inyección de cuadros (AFMF).
- **Tiempo de Cuadro (Frametime):** Medido en milisegundos (ms) para control de estabilidad gráfica.
- **Carga del Núcleo GPU:** Porcentaje de uso de la unidad de procesamiento gráfico.
- **Temperatura GPU:** Temperatura del núcleo de la tarjeta de video AMD en °C.
- **Consumo Eléctrico:** Board Power Draw medido en Watts (W).
- **Uso de VRAM:** Memoria dedicada asignada en Gigabytes (GB).

### Columna 2: Red y Almacenamiento (Infraestructura Local)

- **Velocidad de Red - Bajada (Download):** Tráfico entrante al PC principal medido en MB/s.
- **Velocidad de Red - Subida (Upload):** Tráfico saliente de red local (mide el comportamiento del envío de datos).
- **Espacio en Discos:** Espacio libre disponible (GB) y porcentaje de ocupación por unidad lógica.
- **Temperatura de Almacenamiento:** Estado térmico en °C de las unidades SSD NVMe/SATA y HDD.

### Columna 3: Procesamiento y Multimedia

- **Carga de CPU:** Porcentaje total de procesamiento central del microprocesador.
- **Temperatura de CPU:** Estado térmico global del procesador en °C.
- **Uso de Memoria RAM:** Capacidad de memoria volátil ocupada en Gigabytes (GB) frente al total disponible.
- **Widget YouTube Premium:** Visualización de texto plano estructurado como `[Título del Video/Canción] - [Canal/Artista]`.

## 5. Estructura del Mockup Visual (Layout 16:10)

La interfaz se dividirá en una estructura simétrica de tres columnas fijas para ajustarse a la pantalla de la tableta en modo horizontal sin generar barras de desplazamiento horizontales o verticales:

```
+-----------------------------------------------------------------------------------------+
|                               PANEL DE TELEMETRÍA LOCAL                                 |
+----------------------------+----------------------------+-------------------------------+
| COLUMNA 1: GAMING & GPU    | COLUMNA 2: RED Y DISCOS    | COLUMNA 3: SISTEMA & MEDIA    |
| - FPS: [Valor]             | - Red Down: [Valor] MB/s   | - CPU Load: [Valor] %         |
| - Frametime: [Valor] ms    | - Red Up: [Valor] MB/s     | - CPU Temp: [Valor] °C        |
| - GPU Load: [Valor] %      | - SSD Temp: [Valor] °C     | - RAM Used: [Valor] GB        |
| - GPU Temp: [Valor] °C     | - SSD Free: [Valor] GB     |                               |
| - Power: [Valor] W         | - HDD Temp: [Valor] °C     | - REPRODUCIENDO AHORA:        |
| - VRAM: [Valor] GB         | - HDD Free: [Valor] GB     |   "[Título] - YouTube"        |
+----------------------------+----------------------------+-------------------------------+
```

## 6. Plan de Implementación por Fases (Desarrollo Colaborativo)

Para asegurar que puedas intervenir directamente en el código de forma segura y ágil, dividiremos el desarrollo en módulos desacoplados:

- **Fase 1: Configuración del Entorno de Entrada (Inputs):** Mapeo de rutas de archivos de log de AMD Adrenalin y verificación de permisos WMI para temperaturas en Windows.

- **Fase 2: Construcción del Backend Core en Python:** Creación del script para recolectar datos mediante funciones individuales para cada componente (una función para Red, otra para AMD, otra para Discos). Esto permite modificar o añadir nuevas métricas fácilmente sin romper el resto del servidor.

- **Fase 3: Diseño de la Plantilla HTML/CSS:** Creación de un archivo `index.html` plano con variables embebidas (estilo Jinja2 de Flask) estructurado con clases CSS limpias para la visualización en bloques de color (Verde/Amarillo/Rojo) de acuerdo al nivel de carga o calor.

- **Fase 4: Pruebas locales y Despliegue en Red Interna:** Levantamiento del servicio en el PC y validación de acceso desde el navegador web ligero de la Huawei MediaPad 10 Link.