@echo off
setlocal

REM =============================================================================
REM Verity MVP - Run Dev (Windows)
REM - Starts backend on http://localhost:8001
REM - Starts frontend on http://localhost:3000 (Vite)
REM =============================================================================

REM Resolve repo root (this file is in scripts\)
set "REPO_ROOT=%~dp0.."

REM --- Backend ---
if not exist "%REPO_ROOT%\.venv\Scripts\python.exe" (
  echo ERROR: Python venv not found at %REPO_ROOT%\.venv
  echo Run: scripts\setup.ps1
  exit /b 1
)

REM --- Frontend ---
if not exist "%REPO_ROOT%\frontend\package.json" (
  echo ERROR: frontend\package.json not found. Wrong repo root?
  exit /b 1
)

echo Starting backend on http://localhost:8001 ...
start "verity-backend" cmd /k "cd /d %REPO_ROOT% && .\.venv\Scripts\python.exe -m uvicorn verity.main:app --host 0.0.0.0 --port 8001"

echo Starting frontend on http://localhost:3000 ...
start "verity-frontend" cmd /k "cd /d %REPO_ROOT%\frontend && set VITE_API_URL=http://localhost:8001 && npm run dev"

echo.
echo Done.
echo - Backend:  http://localhost:8001/docs
echo - Frontend: http://localhost:3000/
echo.
endlocal
