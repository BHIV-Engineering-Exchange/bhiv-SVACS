@echo off
setlocal
cd /d "%~dp0\backend"
call py -3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
