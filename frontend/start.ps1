# Quick start script for Verity frontend (Windows)

Write-Host "🚀 Verity Frontend - Quick Start" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Check if .env.local exists
if (-not (Test-Path .env.local)) {
    Write-Host "⚠️  .env.local not found. Creating from template..." -ForegroundColor Yellow
    Copy-Item .env.example .env.local
    Write-Host "✅ Created .env.local" -ForegroundColor Green
    Write-Host ""
    Write-Host "⚠️  IMPORTANT: Edit .env.local and set your VITE_GEMINI_API_KEY" -ForegroundColor Yellow
    Write-Host "   Get your key from: https://aistudio.google.com/app/apikey" -ForegroundColor Gray
    Write-Host ""
    Read-Host "Press Enter after setting your API key"
}

# Check if node_modules exists
if (-not (Test-Path node_modules)) {
    Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
    npm install
    Write-Host "✅ Dependencies installed" -ForegroundColor Green
}

# Start dev server
Write-Host ""
Write-Host "🌐 Starting Vite dev server..." -ForegroundColor Cyan
Write-Host "   Frontend: http://localhost:5173" -ForegroundColor Gray
Write-Host "   Backend should be running on: http://localhost:8001" -ForegroundColor Gray
Write-Host ""
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

npm run dev
