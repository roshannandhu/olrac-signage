@echo off
echo Starting OLRAC Signage Backend and Frontend...

start "OLRAC Backend (FastAPI)" cmd /k "backend\venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000"
start "OLRAC Frontend (Next.js)" cmd /k "cd frontend && npm run dev"

echo.
echo Both servers are starting in separate windows!
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo Admin:    http://localhost:3000/admin/tenants
