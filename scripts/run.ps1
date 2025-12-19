# =============================================================================
# Verity MVP - Run Script (Windows PowerShell)
# =============================================================================
# Runs the development server
# Usage: .\scripts\run.ps1
# =============================================================================

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Verity MVP - Development Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Check if venv exists
if (-not (Test-Path ".venv")) {
    Write-Host "ERROR: Virtual environment not found. Run setup.ps1 first." -ForegroundColor Red
    exit 1
}

# Activate virtual environment
Write-Host "`nActivating virtual environment..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "WARNING: .env not found. Creating from template..." -ForegroundColor Yellow
    Copy-Item .env.example .env
}

# Start server
Write-Host "`nStarting Uvicorn server..." -ForegroundColor Green
Write-Host "API Docs: http://localhost:8001/docs" -ForegroundColor Cyan
Write-Host "OpenAPI:  http://localhost:8001/openapi.json" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop`n" -ForegroundColor Gray

uvicorn verity.main:app --reload --host 0.0.0.0 --port 8001
