# Starts the GeoConnect React frontend (Vite dev server) on http://localhost:5173

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Frontend = Join-Path $Root "frontend"

if (-not (Test-Path (Join-Path $Frontend "node_modules"))) {
    Write-Host "Running npm install first (node_modules missing)..." -ForegroundColor Yellow
    Push-Location $Frontend
    npm install
    Pop-Location
}

Write-Host "Starting GeoConnect frontend on http://localhost:5173 ..." -ForegroundColor Cyan
Push-Location $Frontend
npm run dev
Pop-Location