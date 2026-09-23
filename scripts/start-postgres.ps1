# Starts the GeoConnect PostgreSQL instance (ZIP distribution, not a service).
# Memurai (Redis) runs as a Windows service and starts automatically.

$ErrorActionPreference = "Stop"

$PgBin = "C:\Users\hp\Tools\postgresql\pgsql\bin"
$PgData = "C:\Users\hp\Tools\postgresql\data"
$PgLog = "C:\Users\hp\Tools\postgresql\pg.log"

Write-Host "Checking PostgreSQL on 127.0.0.1:5432 ..." -ForegroundColor Cyan
if (Get-NetTCPConnection -State Listen -LocalPort 5432 -ErrorAction SilentlyContinue) {
    Write-Host "PostgreSQL is already running." -ForegroundColor Green
    exit 0
}

if (-not (Test-Path "$PgBin\postgres.exe")) {
    Write-Host "ERROR: PostgreSQL binaries not found at $PgBin" -ForegroundColor Red
    exit 1
}

& "$PgBin\pg_ctl.exe" -D $PgData -l $PgLog -o "-p 5432 -c listen_addresses=127.0.0.1" start
if ($LASTEXITCODE -eq 0) {
    Write-Host "PostgreSQL started on 127.0.0.1:5432" -ForegroundColor Green
} else {
    Write-Host "PostgreSQL failed to start (see $PgLog)" -ForegroundColor Red
}