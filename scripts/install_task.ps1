# install_task.ps1 — Registra KIRA Telemetry en Task Scheduler
# Ejecutar como Administrador desde la raiz del proyecto:
#   PowerShell -ExecutionPolicy Bypass -File scripts\install_task.ps1

#Requires -RunAsAdministrator

$ErrorActionPreference = "Stop"

$taskName    = "KIRA-Telemetry"
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonExe   = Join-Path $projectRoot ".venv\Scripts\pythonw.exe"
$mainScript  = Join-Path $projectRoot "main.py"

if (-not (Test-Path $pythonExe)) {
    Write-Error "No se encontro .venv\Scripts\pythonw.exe — ejecuta 'uv sync' primero."
    exit 1
}
if (-not (Test-Path $mainScript)) {
    Write-Error "No se encontro main.py en $projectRoot"
    exit 1
}

# Eliminar tarea anterior si ya existe
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction `
    -Execute          $pythonExe `
    -Argument         "`"$mainScript`"" `
    -WorkingDirectory $projectRoot

# AtLogOn del usuario actual — corre en la sesion del usuario, no en Sesion 0
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit    0 `
    -RestartCount          3 `
    -RestartInterval       (New-TimeSpan -Minutes 1) `
    -StartWhenAvailable    `
    -DisallowStartIfOnBatteries $false `
    -StopIfGoingOnBatteries     $false

# Interactive = sesion del usuario (multimedia funciona)
# Highest = admin (necesario para LibreHardwareMonitor / GPU sensors)
$principal = New-ScheduledTaskPrincipal `
    -UserId    $env:USERNAME `
    -LogonType Interactive `
    -RunLevel  Highest

Register-ScheduledTask `
    -TaskName  $taskName `
    -Action    $action `
    -Trigger   $trigger `
    -Settings  $settings `
    -Principal $principal `
    -Force | Out-Null

Write-Host ""
Write-Host "Tarea '$taskName' registrada."
Write-Host "Se iniciara automaticamente al hacer login."
Write-Host ""
Write-Host "Comandos utiles:"
Write-Host "  Iniciar ahora  ->  Start-ScheduledTask  -TaskName '$taskName'"
Write-Host "  Detener        ->  Stop-ScheduledTask   -TaskName '$taskName'"
Write-Host "  Ver estado     ->  Get-ScheduledTask    -TaskName '$taskName' | Select-Object State"
Write-Host "  Desinstalar    ->  scripts\uninstall_task.ps1"
Write-Host ""

$start = Read-Host "Iniciar el panel ahora? (s/n)"
if ($start -eq "s") {
    Start-ScheduledTask -TaskName $taskName
    Write-Host "Panel iniciado. Abre http://localhost:7842"
}
