@echo off
setlocal
title PRJ_232 - Electrical Substation AI

:: Switch safely to project directory (dot prevents trailing slash quote escaping bug)
cd /d "%~dp0."

set "PROJECT_DIR=%CD%"
set "PYTHON_EXE=%PROJECT_DIR%\.venv\Scripts\python.exe"

echo ============================================================
echo   PRJ_232: AI-Powered Maintenance Chatbot for Substations
echo ============================================================
echo.
echo Project Directory: %PROJECT_DIR%
echo.

echo [1/3] Checking Python virtual environment...
if not exist "%PYTHON_EXE%" (
    echo [WARNING] Could not find python.exe at:
    echo   "%PYTHON_EXE%"
    echo.
    echo Searching for alternate virtual environments in project...
    if exist "%PROJECT_DIR%\venv\Scripts\python.exe" (
        set "PYTHON_EXE=%PROJECT_DIR%\venv\Scripts\python.exe"
    ) else (
        echo [ERROR] No virtual environment found.
        echo Attempting to recreate .venv using Python...
        python -m venv "%PROJECT_DIR%\.venv"
        if exist "%PROJECT_DIR%\.venv\Scripts\python.exe" (
            set "PYTHON_EXE=%PROJECT_DIR%\.venv\Scripts\python.exe"
            echo Installing requirements...
            "%PYTHON_EXE%" -m pip install -r "%PROJECT_DIR%\requirements.txt"
        ) else (
            echo Failed to create virtual environment automatically.
            pause
            exit /b 1
        )
    )
)

echo Python Virtual Environment located:
echo   "%PYTHON_EXE%"
echo.

echo [2/3] Launching web browser for Substation AI UI...
start "" "http://127.0.0.1:8000"

echo [3/3] Starting FastAPI backend server...
echo Server running at: http://127.0.0.1:8000
echo Documentation at:  http://127.0.0.1:8000/docs
echo.
echo ============================================================
echo Press Ctrl+C in this window to stop the server at any time.
echo ============================================================
echo.

"%PYTHON_EXE%" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] The server exited with error code %ERRORLEVEL%.
    pause
)
