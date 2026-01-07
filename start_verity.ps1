# SECURITY: Never hardcode secrets in scripts
# Set these in your environment or .env.local file instead

if (-not $env:GEMINI_API_KEY) {
    Write-Host "ERROR: GEMINI_API_KEY not found in environment" -ForegroundColor Red
    Write-Host "Set it with: `$env:GEMINI_API_KEY = 'your-key-here'" -ForegroundColor Yellow
    exit 1
}

if (-not $env:SUPABASE_SERVICE_KEY) {
    Write-Host "WARNING: SUPABASE_SERVICE_KEY not set (optional for dev)" -ForegroundColor Yellow
}

$env:LEGACY_COMPAT_ENABLED = 'false'
$env:AUTH_OTP_INSECURE_DEV_BYPASS = 'true'
$env:SUPABASE_URL = 'https://iruixiqspjcxsmucyylt.supabase.co'
$env:PYTHONPATH = 'c:\Users\ofgarcia\Desktop\Github-Projects\verity-mvp\src'

python -m uvicorn verity.main:app --host 127.0.0.1 --port 8001
