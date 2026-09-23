# Starts the GeoConnect Django backend on http://127.0.0.1:8080 (ASGI/Daphne).

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Python = Join-Path $Backend ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Host "ERROR: virtualenv not found at $Python" -ForegroundColor Red
    Write-Host "Create it first with:  python -m venv backend\.venv"
    exit 1
}

Write-Host "Starting GeoConnect backend on http://127.0.0.1:8080 ..." -ForegroundColor Cyan
& $Python (Join-Path $Backend "manage.py") runserver 127.0.0.1:8080