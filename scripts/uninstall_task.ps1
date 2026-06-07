# uninstall_task.ps1 — Elimina la tarea KIRA Telemetry del Task Scheduler
# Ejecutar como Administrador:
#   PowerShell -ExecutionPolicy Bypass -File scripts\uninstall_task.ps1

#Requires -RunAsAdministrator

$taskName = "KIRA-Telemetry"

$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if (-not $task) {
    Write-Host "La tarea '$taskName' no existe."
    exit 0
}

Stop-ScheduledTask  -TaskName $taskName -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false

Write-Host "Tarea '$taskName' eliminada."
