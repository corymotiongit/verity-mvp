@echo off
cd /d "F:\Github-Projects\verity-mvp"
"F:/Github-Projects/verity-mvp/.venv/Scripts/python.exe" -m uvicorn verity.main:app --port 8000
