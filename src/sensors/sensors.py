import subprocess

def get_cpu_load() -> float:
    """
    Obtiene la carga actual de la CPU del Host (Windows) consultando WMI.
    
    Retorna:
        float: Porcentaje de uso real de la CPU.
    """
    try:
        # Consultamos el contador de rendimiento cacheado para evitar el pico de CPU
        cmd = [
            'powershell.exe',
            '-NoProfile',
            '-Command',
            '(Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor -Filter "Name=\'_Total\'").PercentProcessorTime'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Limpiamos los espacios y convertimos a flotante
        load = result.stdout.strip().replace(',', '.')
        return float(load) if load else 0.0
    except Exception as e:
        print(f"Error obteniendo carga de CPU de Windows: {e}")
        return 0.0

def get_ram_usage() -> dict:
    """
    Obtiene la memoria RAM total y usada del Host (Windows) consultando Win32_OperatingSystem.
    
    Retorna:
        dict: Diccionario con total_gb, used_gb y percent.
    """
    try:
        cmd = [
            'powershell.exe', 
            '-NoProfile', 
            '-Command', 
            '$os = Get-CimInstance Win32_OperatingSystem; Write-Output "$($os.TotalVisibleMemorySize) $($os.FreePhysicalMemory)"'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Los valores retornados por WMI están en Kilobytes (KB)
        total_kb, free_kb = map(int, result.stdout.strip().split())
        
        # Convertimos de KB a GB (dividimos por 1024^2)
        total_gb = total_kb / (1024 ** 2)
        free_gb = free_kb / (1024 ** 2)
        used_gb = total_gb - free_gb
        percent = (used_gb / total_gb) * 100
        
        return {
            "total_gb": round(total_gb, 2),
            "used_gb": round(used_gb, 2),
            "percent": round(percent, 1)
        }
    except Exception as e:
        print(f"Error obteniendo uso de RAM de Windows: {e}")
        return {"total_gb": 0.0, "used_gb": 0.0, "percent": 0.0}

def get_gpu_metrics() -> dict:
    """
    Obtiene el uso y la temperatura (si es accesible) de la GPU del Host (Windows).
    Utiliza WMI/contadores de rendimiento nativos en lugar de utilidades propietarias.
    
    Retorna:
        dict: Diccionario con gpu_usage (float) y gpu_temp (float).
    """
    metrics = {"gpu_usage": 0.0, "gpu_temp": 0.0}
    
    try:
        # Sumamos el porcentaje de utilización de los motores (engines) de la GPU
        cmd_usage = [
            'powershell.exe',
            '-NoProfile',
            '-Command',
            '$gpu = Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine | Measure-Object -Property UtilizationPercentage -Sum; if ($gpu.Sum) { Write-Output $gpu.Sum } else { Write-Output 0 }'
        ]
        result = subprocess.run(cmd_usage, capture_output=True, text=True, check=True)
        usage_val = result.stdout.strip().replace(',', '.')
        
        if usage_val:
            metrics["gpu_usage"] = round(min(float(usage_val), 100.0), 1)
    except Exception as e:
        print(f"Error obteniendo uso de GPU de Windows: {e}")
        
    # Asignamos valor base a la temperatura por si no es accesible directamente mediante WMI nativo
    metrics["gpu_temp"] = 0.0

    return metrics

if __name__ == "__main__":
    print("--- Pruebas del Módulo de Sensores Nativos de Windows ---")
    print(f"Carga de CPU Windows : {get_cpu_load()} %")
    
    ram = get_ram_usage()
    print(f"RAM Total Windows    : {ram['total_gb']} GB")
    print(f"RAM Usada Windows    : {ram['used_gb']} GB")
    print(f"Porcentaje de RAM    : {ram['percent']} %")

    gpu = get_gpu_metrics()
    print(f"Uso de GPU Windows   : {gpu['gpu_usage']} %")
    print(f"Temp. GPU Windows    : {gpu['gpu_temp']} °C")
