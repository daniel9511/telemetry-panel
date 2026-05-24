# Requiere permisos de Administrador
if (!([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Warning "Este script necesita permisos de Administrador. Relanzando..."
    Start-Process powershell -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    Exit
}

# Obtener la IP actual de WSL2
$wsl_ip = (wsl hostname -I).Trim() -split ' ' | Select-Object -First 1

if ([string]::IsNullOrWhiteSpace($wsl_ip)) {
    Write-Error "No se pudo obtener la dirección IP de WSL."
    Exit
}

# Borrar la regla anterior en el puerto 8080
Write-Host "Borrando regla anterior en el puerto 8080..." -ForegroundColor Cyan
netsh interface portproxy delete v4tov4 listenport=8080 listenaddress=0.0.0.0 | Out-Null

# Crear la nueva regla
Write-Host "Creando nueva regla de portproxy hacia $wsl_ip en el puerto 8080..." -ForegroundColor Cyan
netsh interface portproxy add v4tov4 listenport=8080 listenaddress=0.0.0.0 connectport=8080 connectaddress=$wsl_ip | Out-Null

# Imprimir mensaje de éxito en color verde
Write-Host "¡Puente de red configurado exitosamente!" -ForegroundColor Green
Write-Host "Windows (0.0.0.0:8080) -> WSL2 ($wsl_ip:8080)" -ForegroundColor Green
