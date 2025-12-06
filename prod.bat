@echo off
REM ===================================================================
REM RAG Chatbot - Production Mode Runner (Windows)
REM ===================================================================
REM This script runs the project in production mode with Docker
REM ===================================================================

setlocal EnableDelayedExpansion

REM Colors using Windows ANSI escape codes (Windows 10+)
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "BLUE=[94m"
set "CYAN=[96m"
set "NC=[0m"

REM ===================================================================
REM Print Functions
REM ===================================================================

:print_header
echo.
echo %BLUE%================================================================%NC%
echo %BLUE%  %~1%NC%
echo %BLUE%================================================================%NC%
echo.
exit /b

:print_success
echo %GREEN%[+] %~1%NC%
exit /b

:print_warning
echo %YELLOW%[!] %~1%NC%
exit /b

:print_error
echo %RED%[X] %~1%NC%
exit /b

:print_info
echo %CYAN%[i] %~1%NC%
exit /b

REM ===================================================================
REM Check Prerequisites
REM ===================================================================

:check_prerequisites
call :print_header "Checking Prerequisites"

REM Check Docker
where docker >nul 2>&1
if %errorlevel% neq 0 (
    call :print_error "Docker not found!"
    call :print_info "Install from: https://docs.docker.com/desktop/install/windows-install/"
    pause
    exit /b 1
)

REM Check Docker Compose
where docker-compose >nul 2>&1
if %errorlevel% neq 0 (
    call :print_error "Docker Compose not found!"
    call :print_info "Install Docker Desktop which includes Docker Compose"
    pause
    exit /b 1
)

for /f "tokens=3 delims=, " %%i in ('docker --version 2^>^&1') do set DOCKER_VERSION=%%i
for /f "tokens=3 delims=, " %%i in ('docker-compose --version 2^>^&1') do set COMPOSE_VERSION=%%i

call :print_success "Docker: !DOCKER_VERSION!"
call :print_success "Docker Compose: !COMPOSE_VERSION!"

exit /b 0

REM ===================================================================
REM Check .env File
REM ===================================================================

:check_env
call :print_header "Checking Environment Configuration"

if not exist ".env" (
    call :print_warning ".env file not found"
    call :print_info "Creating from .env.example..."
    copy .env.example .env >nul
    call :print_error "Please edit .env and configure production settings!"
    pause
    exit /b 1
)

REM Check critical variables
set "missing_vars="

findstr /C:"GOOGLE_API_KEY=your_google_api_key_here" .env >nul
if %errorlevel% equ 0 (
    set "missing_vars=!missing_vars! GOOGLE_API_KEY"
)

findstr /C:"JWT_SECRET_KEY=change-this" .env >nul
if %errorlevel% equ 0 (
    set "missing_vars=!missing_vars! JWT_SECRET_KEY"
)

if not "!missing_vars!"=="" (
    call :print_error "Missing configuration:!missing_vars!"
    call :print_info "Please configure these variables in .env"
    pause
    exit /b 1
)

call :print_success "Environment configuration valid"

exit /b 0

REM ===================================================================
REM Build Docker Images
REM ===================================================================

:build_images
call :print_header "Building Docker Images"

call :print_info "This may take several minutes on first run..."

cd docker

REM Check for --no-cache flag
if "%~1"=="--no-cache" (
    call :print_info "Building with --no-cache..."
    docker-compose build --no-cache
) else (
    docker-compose build
)

if %errorlevel% neq 0 (
    call :print_error "Docker build failed"
    cd ..
    pause
    exit /b 1
)

cd ..

call :print_success "Docker images built successfully"

exit /b 0

REM ===================================================================
REM Start Services
REM ===================================================================

:start_services
call :print_header "Starting Production Services"

cd docker

REM Check what profile to use
set "PROFILE="

set /p "include_frontend=Include frontend container? (y/N): "
if /i "!include_frontend!"=="y" (
    set "PROFILE=--profile dev"
    call :print_info "Starting with frontend (dev profile)..."
)

REM Start services
call :print_info "Starting containers..."
docker-compose !PROFILE! up -d

if %errorlevel% neq 0 (
    call :print_error "Failed to start services"
    cd ..
    pause
    exit /b 1
)

cd ..

REM Wait for services to be healthy
call :print_info "Waiting for services to be ready..."
timeout /t 5 /nobreak >nul

call :print_success "Services started"

exit /b 0

REM ===================================================================
REM Stop Services
REM ===================================================================

:stop_services
call :print_header "Stopping Production Services"

cd docker
docker-compose down
cd ..

call :print_success "Services stopped"

exit /b 0

REM ===================================================================
REM Show Logs
REM ===================================================================

:show_logs
call :print_header "Service Logs"

cd docker

call :print_info "Showing logs (Ctrl+C to exit)..."
docker-compose logs -f --tail=100

cd ..

exit /b 0

REM ===================================================================
REM Show Status
REM ===================================================================

:show_status
call :print_header "Service Status"

cd docker
docker-compose ps
cd ..

echo.
call :print_info "Access points:"
echo   API: %GREEN%http://localhost:8000%NC%
echo   API Docs: %GREEN%http://localhost:8000/docs%NC%
echo   PostgreSQL: %GREEN%localhost:5432%NC%

REM Check if frontend is running
docker ps | findstr "chatbot-frontend" >nul 2>&1
if %errorlevel% equ 0 (
    echo   Frontend: %GREEN%http://localhost:3000%NC%
)

echo.

exit /b 0

REM ===================================================================
REM Restart Services
REM ===================================================================

:restart_services
call :print_header "Restarting Services"

call :stop_services
timeout /t 2 /nobreak >nul
call :start_services
timeout /t 2 /nobreak >nul
call :show_status

exit /b 0

REM ===================================================================
REM Run Database Migrations
REM ===================================================================

:run_migrations
call :print_header "Running Database Migrations"

cd docker

call :print_info "Executing Alembic migrations..."

REM Run migrations in backend container
docker-compose exec backend alembic upgrade head

if %errorlevel% neq 0 (
    call :print_error "Migrations failed"
    cd ..
    pause
    exit /b 1
)

cd ..

call :print_success "Migrations completed"

exit /b 0

REM ===================================================================
REM Backup Database
REM ===================================================================

:backup_database
call :print_header "Backing Up Database"

set "BACKUP_DIR=backups"
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c%%a%%b)
for /f "tokens=1-2 delims=/: " %%a in ('time /t') do (set mytime=%%a%%b)
set "TIMESTAMP=%mydate%_%mytime%"
set "BACKUP_FILE=%BACKUP_DIR%\chatbot_db_%TIMESTAMP%.sql"

call :print_info "Creating backup: %BACKUP_FILE%"

cd docker

REM Get database credentials from .env or use defaults
for /f "tokens=2 delims==" %%i in ('findstr /C:"DB_NAME=" ..\.env 2^>nul') do set DB_NAME=%%i
for /f "tokens=2 delims==" %%i in ('findstr /C:"DB_USER=" ..\.env 2^>nul') do set DB_USER=%%i

if "%DB_NAME%"=="" set DB_NAME=chatbot_db
if "%DB_USER%"=="" set DB_USER=postgres

REM Create backup
docker-compose exec -T postgres pg_dump -U "%DB_USER%" "%DB_NAME%" > "..\%BACKUP_FILE%"

cd ..

if exist "%BACKUP_FILE%" (
    for %%A in ("%BACKUP_FILE%") do set BACKUP_SIZE=%%~zA
    call :print_success "Backup created: %BACKUP_FILE% (!BACKUP_SIZE! bytes)"
) else (
    call :print_error "Backup failed"
    pause
    exit /b 1
)

exit /b 0

REM ===================================================================
REM Restore Database
REM ===================================================================

:restore_database
call :print_header "Restoring Database"

set "BACKUP_DIR=backups"

if not exist "%BACKUP_DIR%" (
    call :print_error "Backup directory not found"
    pause
    exit /b 1
)

REM List available backups
call :print_info "Available backups:"
dir /b "%BACKUP_DIR%\*.sql" 2>nul

echo.
set /p "BACKUP_FILE=Enter backup filename to restore: "

if not exist "%BACKUP_DIR%\%BACKUP_FILE%" (
    call :print_error "Backup file not found: %BACKUP_DIR%\%BACKUP_FILE%"
    pause
    exit /b 1
)

call :print_warning "This will overwrite the current database!"
set /p "CONFIRM=Are you sure? (yes/NO): "

if not "!CONFIRM!"=="yes" (
    call :print_info "Restore cancelled"
    exit /b 0
)

cd docker

REM Get database credentials
for /f "tokens=2 delims==" %%i in ('findstr /C:"DB_NAME=" ..\.env 2^>nul') do set DB_NAME=%%i
for /f "tokens=2 delims==" %%i in ('findstr /C:"DB_USER=" ..\.env 2^>nul') do set DB_USER=%%i

if "%DB_NAME%"=="" set DB_NAME=chatbot_db
if "%DB_USER%"=="" set DB_USER=postgres

call :print_info "Restoring from %BACKUP_FILE%..."

REM Restore backup
type "..\%BACKUP_DIR%\%BACKUP_FILE%" | docker-compose exec -T postgres psql -U "%DB_USER%" "%DB_NAME%"

cd ..

call :print_success "Database restored"

exit /b 0

REM ===================================================================
REM Show Production Info
REM ===================================================================

:show_production_info
call :print_header "Production Configuration"

echo.
echo Services:
echo   - Backend (FastAPI)
echo   - PostgreSQL with pgvector
echo   - Frontend (optional)
echo.
echo Features (from .env):

REM Show feature status
findstr /C:"USE_LANGCHAIN_CHUNKING=true" .env >nul 2>&1
if %errorlevel% equ 0 (
    echo   - Semantic Chunking: %GREEN%[+] Enabled%NC%
) else (
    echo   - Semantic Chunking: %YELLOW%[X] Disabled%NC%
)

findstr /C:"OCR_ENABLED=true" .env >nul 2>&1
if %errorlevel% equ 0 (
    echo   - OCR (Tesseract^): %GREEN%[+] Enabled%NC%
) else (
    echo   - OCR (Tesseract^): %YELLOW%[X] Disabled%NC%
)

findstr /C:"USE_FAISS=true" .env >nul 2>&1
if %errorlevel% equ 0 (
    echo   - FAISS Acceleration: %GREEN%[+] Enabled%NC%
) else (
    echo   - FAISS Acceleration: %YELLOW%[X] Disabled%NC%
)

findstr /C:"MULTI_QUERY_ENABLED=true" .env >nul 2>&1
if %errorlevel% equ 0 (
    echo   - Multi-Query: %GREEN%[+] Enabled%NC%
) else (
    echo   - Multi-Query: %YELLOW%[X] Disabled%NC%
)

echo.
echo Production Optimizations:
echo   - Gunicorn workers: 4
echo   - DB connection pool: 50 (max 100)
echo   - Auto-restart on failure
echo   - Health checks enabled
echo.

exit /b 0

REM ===================================================================
REM Main Execution
REM ===================================================================

set "COMMAND=%~1"

if "%COMMAND%"=="" set "COMMAND=start"

if /i "%COMMAND%"=="start" goto :cmd_start
if /i "%COMMAND%"=="stop" goto :cmd_stop
if /i "%COMMAND%"=="restart" goto :cmd_restart
if /i "%COMMAND%"=="rebuild" goto :cmd_rebuild
if /i "%COMMAND%"=="logs" goto :cmd_logs
if /i "%COMMAND%"=="status" goto :cmd_status
if /i "%COMMAND%"=="migrate" goto :cmd_migrate
if /i "%COMMAND%"=="backup" goto :cmd_backup
if /i "%COMMAND%"=="restore" goto :cmd_restore
if /i "%COMMAND%"=="info" goto :cmd_info
if /i "%COMMAND%"=="shell" goto :cmd_shell

REM Show usage
echo Usage: prod.bat {start^|stop^|restart^|rebuild^|logs^|status^|migrate^|backup^|restore^|info^|shell}
echo.
echo Commands:
echo   start    - Build and start all services (default)
echo   stop     - Stop all services
echo   restart  - Restart all services
echo   rebuild  - Rebuild images and restart (use after code changes)
echo   logs     - Show service logs
echo   status   - Show service status and access points
echo   migrate  - Run database migrations
echo   backup   - Create database backup
echo   restore  - Restore database from backup
echo   info     - Show production configuration
echo   shell    - Open shell in backend container
echo.
echo Examples:
echo   prod.bat start          # Start production environment
echo   prod.bat logs           # View logs
echo   prod.bat rebuild        # Rebuild after code changes
echo   prod.bat backup         # Create database backup
echo.
pause
exit /b 1

:cmd_start
call :check_prerequisites
call :check_env
call :build_images
call :start_services
call :show_status
exit /b 0

:cmd_stop
call :stop_services
exit /b 0

:cmd_restart
call :restart_services
exit /b 0

:cmd_rebuild
call :check_prerequisites
call :check_env
call :build_images --no-cache
call :restart_services
exit /b 0

:cmd_logs
call :show_logs
exit /b 0

:cmd_status
call :show_status
exit /b 0

:cmd_migrate
call :run_migrations
exit /b 0

:cmd_backup
call :backup_database
exit /b 0

:cmd_restore
call :restore_database
exit /b 0

:cmd_info
call :show_production_info
exit /b 0

:cmd_shell
call :print_header "Opening Shell in Backend Container"
cd docker
docker-compose exec backend /bin/bash
cd ..
exit /b 0
