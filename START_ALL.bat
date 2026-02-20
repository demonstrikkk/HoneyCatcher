@echo off
REM HoneyBadger Quick Start - Complete System
REM Starts backend, frontend, and ngrok tunnels

echo ========================================
echo   HoneyBadger - Complete System Start
echo ========================================
echo.

REM Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found in PATH
    pause
    exit /b 1
)

REM Check if Node.js is installed
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Node.js not found in PATH
    pause
    exit /b 1
)

echo [1/3] Starting Backend Server...
start "HoneyBadger Backend" cmd /k "cd honeypot\backend && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"
timeout /t 3 >nul

echo [2/3] Starting Frontend Server...
start "HoneyBadger Frontend" cmd /k "cd honeypot\frontend && npm run dev"
timeout /t 3 >nul

echo [3/3] Starting ngrok Tunnels (optional)...
echo.
echo Do you want to start ngrok tunnels? (Y/N)
choice /c YN /n
if %ERRORLEVEL% EQU 1 (
    start "ngrok Tunnels" cmd /k "ngrok start --all"
)

echo.
echo ========================================
echo   All Services Started!
echo ========================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo API Docs: http://localhost:8000/docs
echo.
echo Press any key to open browser...
pause >nul

start http://localhost:5173

echo.
echo System is running! Close this window to keep services running.
echo.
pause
