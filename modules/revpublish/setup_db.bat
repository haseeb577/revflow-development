@echo off
echo ========================================
echo RevPublish - Database Setup
echo ========================================
echo.

REM Check if PostgreSQL is available
where psql >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] PostgreSQL is not installed or not in PATH
    echo Please install PostgreSQL from: https://www.postgresql.org/download/windows/
    echo.
    pause
    exit /b 1
)

echo [INFO] PostgreSQL found
echo.

REM Database configuration (from .env or defaults)
set DB_NAME=revflow
set DB_USER=revflow
set DB_PASSWORD=revflow2026
set DB_HOST=localhost
set DB_PORT=5432

echo [INFO] Setting up database tables...
echo Database: %DB_NAME%
echo User: %DB_USER%
echo.

echo Please enter your PostgreSQL password (for user %DB_USER%):
psql -U %DB_USER% -d %DB_NAME% -f backend\setup_database.sql

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Database tables created successfully!
    echo.
) else (
    echo.
    echo [ERROR] Database setup failed.
    echo.
    echo Troubleshooting:
    echo 1. Ensure PostgreSQL is running
    echo 2. Check database credentials
    echo 3. Verify database '%DB_NAME%' exists
    echo 4. Verify user '%DB_USER%' has permissions
    echo.
)

pause


