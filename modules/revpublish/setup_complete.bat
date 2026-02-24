@echo off
echo ========================================
echo RevPublish - Complete Setup Script
echo ========================================
echo.

REM Step 1: Check PostgreSQL
echo [STEP 1] Checking PostgreSQL...
where psql >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] PostgreSQL is not installed!
    echo.
    echo Please install PostgreSQL from:
    echo https://www.postgresql.org/download/windows/
    echo.
    echo After installation, run this script again.
    echo.
    pause
    exit /b 1
)

echo [OK] PostgreSQL is installed
echo.

REM Step 2: Check if PostgreSQL service is running
echo [STEP 2] Checking PostgreSQL service...
netstat -ano | findstr :5432 >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] PostgreSQL service is not running
    echo.
    echo Please start PostgreSQL service:
    echo 1. Press Win+R, type: services.msc
    echo 2. Find "PostgreSQL" service
    echo 3. Right-click and select "Start"
    echo.
    echo OR run as Administrator:
    echo    net start postgresql-x64-15
    echo.
    set /p continue="Continue anyway? (y/n): "
    if /i not "%continue%"=="y" (
        exit /b 1
    )
) else (
    echo [OK] PostgreSQL service is running
)
echo.

REM Step 3: Check Python
echo [STEP 3] Checking Python...
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed!
    echo Please install Python 3.11+ from: https://www.python.org/downloads/
    pause
    exit /b 1
)

python --version
echo [OK] Python is installed
echo.

REM Step 4: Setup database
echo [STEP 4] Setting up database...
cd backend
if exist setup_db.py (
    python setup_db.py
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo [ERROR] Database setup failed!
        echo.
        echo Common issues:
        echo 1. PostgreSQL service not running
        echo 2. Database 'revflow' doesn't exist
        echo 3. Wrong database credentials
        echo.
        echo Please check BACKEND_SETUP.md for detailed instructions.
        echo.
        cd ..
        pause
        exit /b 1
    )
) else (
    echo [WARNING] setup_db.py not found, skipping database setup
)
cd ..
echo.

REM Step 5: Test database connection
echo [STEP 5] Testing database connection...
cd backend
if exist test_db.py (
    python test_db.py
)
cd ..
echo.

echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Start backend: start_backend.bat
echo 2. Start frontend: npm run dev (in the revpublish folder)
echo 3. Open: http://localhost:3550/revflow_os/revpublish/
echo.
pause


