@echo off
setlocal

echo ============================================================
echo  AcmeParts Cloud - Windows Quick Start
echo ============================================================
echo.

where docker >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not installed or not in PATH.
    echo         Install Docker Desktop: https://www.docker.com/products/docker-desktop/
    exit /b 1
)

echo [1/3] Building containers...
docker compose build
if errorlevel 1 (
    echo [ERROR] docker compose build failed.
    exit /b 1
)

echo.
echo [2/3] Starting services (db + api)...
docker compose up -d
if errorlevel 1 (
    echo [ERROR] docker compose up failed.
    exit /b 1
)

echo.
echo [3/3] Waiting for API to be ready...
timeout /t 8 /nobreak >nul

echo.
echo ============================================================
echo  AcmeParts Cloud is running
echo  Dashboard : http://localhost:8000/
echo  API docs  : http://localhost:8000/docs
echo  To stop   : docker compose down
echo ============================================================
echo.

start "" http://localhost:8000/

endlocal
