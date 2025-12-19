# =============================================================================
# Verity MVP - Setup Script (Windows PowerShell)
# =============================================================================
# Reproducible setup script for Windows development environment
# Usage: .\scripts\setup.ps1
# =============================================================================

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Verity MVP - Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Check Python version
Write-Host "`n[1/5] Checking Python version..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python not found. Please install Python 3.11+" -ForegroundColor Red
    exit 1
}
Write-Host "Found: $pythonVersion" -ForegroundColor Green

# Create virtual environment
Write-Host "`n[2/5] Creating virtual environment..." -ForegroundColor Yellow
if (Test-Path ".venv") {
    Write-Host "Virtual environment already exists, skipping..." -ForegroundColor Gray
} else {
    python -m venv .venv
    Write-Host "Virtual environment created" -ForegroundColor Green
}

# Activate virtual environment
Write-Host "`n[3/5] Activating virtual environment..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "`n[4/5] Installing dependencies..." -ForegroundColor Yellow
pip install --upgrade pip
pip install -e ".[dev]"
Write-Host "Dependencies installed" -ForegroundColor Green

# Create .env from template
Write-Host "`n[5/5] Setting up environment file..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host ".env already exists, skipping..." -ForegroundColor Gray
} else {
    Copy-Item .env.example .env
    Write-Host ".env created from template" -ForegroundColor Green
    Write-Host "IMPORTANT: Edit .env with your Supabase and GCP credentials" -ForegroundColor Yellow
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Setup Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`nNext steps:"
Write-Host "  1. Edit .env with your credentials"
Write-Host "  2. Run: .\scripts\run.ps1"
Write-Host "  3. Visit: http://localhost:8001/docs"
