# Script de validación completa para beta con datos de Spotify
# Ejecuta todo el flujo: setup → carga de datos → tests → métricas

param(
    [switch]$SkipDataLoad,
    [switch]$Cleanup
)

$ErrorActionPreference = "Stop"

Write-Host "=== Verity Beta Validation (Spotify Data) ===" -ForegroundColor Cyan
Write-Host ""

# 1. Verificar que backend está corriendo
Write-Host "[1/5] Checking backend health..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8001/api/v2/health' -TimeoutSec 5
    Write-Host "  ✓ Backend is healthy (dictionary v$($health.dictionary_version))" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Backend not running. Start with: .\scripts\run.ps1" -ForegroundColor Red
    exit 1
}

# 2. Cargar datos de Spotify (si no se skipea)
if (-not $SkipDataLoad) {
    Write-Host ""
    Write-Host "[2/5] Loading Spotify data to Supabase..." -ForegroundColor Yellow
    
    # Verificar que existen las variables de entorno
    if (-not $env:SUPABASE_URL -or -not $env:SUPABASE_SERVICE_KEY) {
        Write-Host "  ⚠ SUPABASE_URL or SUPABASE_SERVICE_KEY not set" -ForegroundColor Yellow
        Write-Host "  Skipping data load. Run manually: python scripts\load_spotify_data.py" -ForegroundColor Yellow
    } else {
        python scripts\load_spotify_data.py
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  ✗ Data load failed" -ForegroundColor Red
            exit 1
        }
        Write-Host "  ✓ Data loaded successfully" -ForegroundColor Green
    }
} else {
    Write-Host ""
    Write-Host "[2/5] Skipping data load (--SkipDataLoad)" -ForegroundColor Yellow
}

# 3. Ejecutar suite de tests
Write-Host ""
Write-Host "[3/5] Running automated test suite..." -ForegroundColor Yellow
python -m pytest tests\test_beta_e2e.py -v --tb=short

if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Tests failed" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ All tests passed" -ForegroundColor Green

# 4. Obtener métricas de observabilidad
Write-Host ""
Write-Host "[4/5] Fetching observability metrics..." -ForegroundColor Yellow
$metrics = Invoke-RestMethod -Uri 'http://127.0.0.1:8001/api/v2/metrics'

Write-Host "  Tool Metrics:" -ForegroundColor Cyan
foreach ($tool in $metrics.tools.PSObject.Properties) {
    $name = $tool.Name
    $data = $tool.Value
    Write-Host "    $name" -ForegroundColor White
    Write-Host "      Calls: $($data.call_count)" -ForegroundColor Gray
    Write-Host "      p50: $($data.p50_ms)ms | p90: $($data.p90_ms)ms | p99: $($data.p99_ms)ms" -ForegroundColor Gray
    
    if ($data.errors.PSObject.Properties.Count -gt 0) {
        Write-Host "      Errors:" -ForegroundColor Yellow
        foreach ($err in $data.errors.PSObject.Properties) {
            Write-Host "        $($err.Name): $($err.Value)" -ForegroundColor Yellow
        }
    }
}

Write-Host ""
Write-Host "  Global Errors:" -ForegroundColor Cyan
if ($metrics.global_errors.PSObject.Properties.Count -gt 0) {
    foreach ($err in $metrics.global_errors.PSObject.Properties) {
        Write-Host "    $($err.Name): $($err.Value)" -ForegroundColor Yellow
    }
} else {
    Write-Host "    None" -ForegroundColor Green
}

Write-Host ""
Write-Host "  OTP Metrics:" -ForegroundColor Cyan
Write-Host "    Attempts: $($metrics.otp.attempts_in_window)" -ForegroundColor Gray
Write-Host "    Success: $($metrics.otp.success_count)" -ForegroundColor Gray

# 5. Cleanup (opcional)
if ($Cleanup) {
    Write-Host ""
    Write-Host "[5/5] Cleaning up test data..." -ForegroundColor Yellow
    Write-Host "  ⚠ Cleanup not implemented. Manually delete from Supabase if needed." -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "[5/5] Skipping cleanup (use --Cleanup to remove test data)" -ForegroundColor Yellow
}

# Resumen final
Write-Host ""
Write-Host "=== Validation Complete ===" -ForegroundColor Green
Write-Host "✓ Backend healthy" -ForegroundColor Green
Write-Host "✓ Data loaded (or skipped)" -ForegroundColor Green
Write-Host "✓ All tests passed" -ForegroundColor Green
Write-Host "✓ Metrics collected" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Review metrics above for performance issues" -ForegroundColor White
Write-Host "  2. Test manually with Postman/curl if needed" -ForegroundColor White
Write-Host "  3. Validate with n8n operational (currently using bypass)" -ForegroundColor White
