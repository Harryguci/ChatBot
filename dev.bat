@echo off
REM ===================================================================
REM RAG Chatbot - Development Mode Runner (Windows)
REM ===================================================================
REM This script runs the project in development mode with hot-reload
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
REM Activate Virtual Environment
REM ===================================================================

if not exist ".venv" (
    call :print_error "Virtual environment not found!"
    call :print_info "Run 'setup.bat' first to set up the project"
    pause
    exit /b 1
)

call :print_info "Activating virtual environment..."

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    call :print_success "Virtual environment activated"
) else (
    call :print_error "Virtual environment activation script not found"
    pause
    exit /b 1
)

REM ===================================================================
REM Check .env File
REM ===================================================================

if not exist ".env" (
    call :print_warning ".env file not found"
    call :print_info "Creating from .env.example..."
    copy .env.example .env >nul
    call :print_warning "Please edit .env and add your API keys before running!"
    pause
    exit /b 1
)

REM Check if GOOGLE_API_KEY is set
findstr /C:"GOOGLE_API_KEY=your_google_api_key_here" .env >nul
if %errorlevel% equ 0 (
    call :print_error "GOOGLE_API_KEY not configured in .env"
    call :print_info "Please edit .env and add your Google API key"
    call :print_info "Get it from: https://makersuite.google.com/app/apikey"
    pause
    exit /b 1
)

call :print_success ".env file configured"

REM ===================================================================
REM Check PostgreSQL
REM ===================================================================

call :print_info "Checking PostgreSQL connection..."

REM Get DB config from .env
for /f "tokens=2 delims==" %%i in ('findstr /C:"DB_HOST=" .env 2^>nul') do set DB_HOST=%%i
for /f "tokens=2 delims==" %%i in ('findstr /C:"DB_PORT=" .env 2^>nul') do set DB_PORT=%%i

if "%DB_HOST%"=="" set DB_HOST=localhost
if "%DB_PORT%"=="" set DB_PORT=5432

REM Check if PostgreSQL is accessible (try with Docker)
where docker >nul 2>&1
if %errorlevel% equ 0 (
    docker ps | findstr "postgres" >nul 2>&1
    if %errorlevel% equ 0 (
        call :print_success "PostgreSQL is running at %DB_HOST%:%DB_PORT%"
    ) else (
        call :print_warning "PostgreSQL container not running"
        call :print_info "Starting PostgreSQL with Docker..."

        cd docker
        docker-compose up -d postgres
        cd ..

        timeout /t 3 /nobreak >nul
        call :print_success "PostgreSQL started"
    )
) else (
    call :print_warning "Cannot verify PostgreSQL status (Docker not available)"
    call :print_info "Assuming PostgreSQL is running at %DB_HOST%:%DB_PORT%"
)

REM ===================================================================
REM Show Development Info
REM ===================================================================

call :print_header "RAG Chatbot - Development Mode"

echo.
echo Development Configuration:
echo   - Hot-reload: %GREEN%Enabled%NC%
echo   - Debug mode: %GREEN%Enabled%NC%
echo   - Auto-restart: %GREEN%Enabled%NC%
echo.
echo Features enabled (check .env):

REM Check feature flags
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
    echo   - Multi-Query Retrieval: %GREEN%[+] Enabled%NC%
) else (
    echo   - Multi-Query Retrieval: %YELLOW%[X] Disabled%NC%
)

echo.
call :print_info "Edit .env to enable/disable features"
echo.

REM ===================================================================
REM Parse Arguments
REM ===================================================================

set "MODE=%~1"
if "%MODE%"=="" set "MODE=all"

if /i "%MODE%"=="backend" goto :start_backend
if /i "%MODE%"=="frontend" goto :start_frontend
if /i "%MODE%"=="all" goto :start_all

echo Usage: dev.bat [backend^|frontend^|all]
echo   backend  - Start only the backend server
echo   frontend - Start only the frontend server
echo   all      - Start both servers (default)
pause
exit /b 1

REM ===================================================================
REM Start Backend
REM ===================================================================

:start_backend
call :print_header "Starting Backend (Development Mode)"

call :print_info "Starting FastAPI server with hot-reload..."
call :print_info "API will be available at: %GREEN%http://localhost:8000%NC%"
call :print_info "API Docs at: %GREEN%http://localhost:8000/docs%NC%"
echo.
call :print_warning "Press Ctrl+C to stop"
echo.

REM Set PYTHONPATH
set PYTHONPATH=%PYTHONPATH%;%CD%\src

REM Run uvicorn with reload
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir src --log-level info

exit /b

REM ===================================================================
REM Start Frontend
REM ===================================================================

:start_frontend
if not exist "frontend\app" (
    call :print_warning "Frontend directory not found. Skipping"
    pause
    exit /b
)

where node >nul 2>&1
if %errorlevel% neq 0 (
    call :print_warning "Node.js not found. Skipping frontend"
    pause
    exit /b
)

call :print_header "Starting Frontend (Development Mode)"

cd frontend\app

call :print_info "Starting React development server..."
call :print_info "Frontend will be available at: %GREEN%http://localhost:3000%NC%"

call npm run dev

cd ..\..

exit /b

REM ===================================================================
REM Start Both Backend and Frontend
REM ===================================================================

:start_all
call :print_header "Starting Full Stack (Development Mode)"

set /p "start_fe=Start frontend development server? (Y/n): "
if /i "!start_fe!"=="n" goto :start_backend_only

REM Check if frontend exists
if not exist "frontend\app" (
    call :print_warning "Frontend directory not found"
    goto :start_backend_only
)

where node >nul 2>&1
if %errorlevel% neq 0 (
    call :print_warning "Node.js not found"
    goto :start_backend_only
)

REM Start frontend in new window
call :print_info "Starting frontend in new window..."
start "RAG Chatbot - Frontend" cmd /k "cd frontend\app && npm run dev"

timeout /t 2 /nobreak >nul

:start_backend_only
REM Start backend in current window
goto :start_backend

exit /b 0
