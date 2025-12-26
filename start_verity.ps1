$env:LEGACY_COMPAT_ENABLED = 'false'
$env:AUTH_OTP_INSECURE_DEV_BYPASS = 'true'
$env:SUPABASE_URL = 'https://iruixiqspjcxsmucyylt.supabase.co'
$env:SUPABASE_SERVICE_KEY = 'REDACTED_SUPABASE_KEY'
$env:GEMINI_API_KEY = 'REDACTED_API_KEY'
$env:PYTHONPATH = 'c:\Users\ofgarcia\Desktop\Github-Projects\verity-mvp\src'
python -m uvicorn verity.main:app --host 127.0.0.1 --port 8001
