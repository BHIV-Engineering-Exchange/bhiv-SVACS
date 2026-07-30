@echo off
setlocal
set "NODEJS_PATH=C:\Program Files\nodejs"
set "PATH=%NODEJS_PATH%;%PATH%"
cd /d "%~dp0\frontend"
call npm.cmd install
call npm.cmd run dev -- --host 0.0.0.0 --port 5173
