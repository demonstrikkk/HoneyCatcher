@echo off
REM Start all ngrok tunnels for HoneyBadger application
REM Make sure ngrok.yml is configured in your home directory

echo ========================================
echo   HoneyBadger - ngrok Multi-Tunnel
echo ========================================
echo.
echo Starting ngrok tunnels...
echo - Frontend (port 5173)
echo - Backend (port 8000)
echo - WebSocket (port 8000)
echo.

REM Check if ngrok is installed
where ngrok >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: ngrok not found in PATH
    echo Please install ngrok from https://ngrok.com/download
    echo.
    pause
    exit /b 1
)

REM Start all tunnels from ngrok.yml
ngrok start --all --config="%USERPROFILE%\.ngrok2\ngrok.yml"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Failed to start ngrok tunnels
    echo Make sure ngrok.yml is configured in: %USERPROFILE%\.ngrok2\ngrok.yml
    echo.
    pause
    exit /b 1
)

pause
