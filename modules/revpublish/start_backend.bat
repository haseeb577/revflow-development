@echo off
echo ========================================
echo Starting RevPublish Backend
echo ========================================
echo.

cd backend

REM Check if Python is available
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.11+ from: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo [INFO] Python found
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies if needed
if not exist "venv\Lib\site-packages\fastapi" (
    echo [INFO] Installing dependencies...
    echo This may take a few minutes...
    pip install --upgrade pip
    pip install -r requirements.txt
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
)

echo.
echo ========================================
echo Starting RevPublish Backend on port 8550
echo ========================================
echo.
echo Backend will be available at: http://localhost:8550
echo API Docs will be at: http://localhost:8550/docs
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start the server
python -m uvicorn main:app --host 0.0.0.0 --port 8550 --reload


