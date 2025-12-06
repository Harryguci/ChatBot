@echo off
REM ===================================================================
REM RAG Chatbot - Project Setup Script (Windows)
REM ===================================================================
REM This script sets up the project environment for the first time
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
REM Main Script
REM ===================================================================

call :print_header "RAG Chatbot - Project Setup (Windows)"
call :print_info "This script will set up your development environment"
echo.

REM ===================================================================
REM Check Prerequisites
REM ===================================================================

call :print_header "Checking Prerequisites"

set "all_good=1"

REM Check Python
where python >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    call :print_success "Python found: !PYTHON_VERSION!"
    set "PYTHON_CMD=python"
) else (
    where python3 >nul 2>&1
    if %errorlevel% equ 0 (
        for /f "tokens=2" %%i in ('python3 --version 2^>^&1') do set PYTHON_VERSION=%%i
        call :print_success "Python 3 found: !PYTHON_VERSION!"
        set "PYTHON_CMD=python3"
    ) else (
        call :print_error "Python not found! Please install Python 3.10 or higher"
        call :print_info "Download from: https://www.python.org/downloads/"
        set "all_good=0"
    )
)

REM Check Node.js
where node >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=1" %%i in ('node --version 2^>^&1') do set NODE_VERSION=%%i
    call :print_success "Node.js found: !NODE_VERSION!"
) else (
    call :print_warning "Node.js not found (optional for frontend development)"
    call :print_info "Download from: https://nodejs.org/"
)

REM Check Docker
where docker >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=3 delims=," %%i in ('docker --version 2^>^&1') do set DOCKER_VERSION=%%i
    call :print_success "Docker found: !DOCKER_VERSION!"
) else (
    call :print_warning "Docker not found (optional for containerized deployment)"
    call :print_info "Download Docker Desktop from: https://docs.docker.com/desktop/install/windows-install/"
)

REM Check Git
where git >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=3" %%i in ('git --version 2^>^&1') do set GIT_VERSION=%%i
    call :print_success "Git found: !GIT_VERSION!"
) else (
    call :print_warning "Git not found"
    call :print_info "Download from: https://git-scm.com/download/win"
)

if "%all_good%"=="0" (
    call :print_error "Please install missing prerequisites and run setup again"
    pause
    exit /b 1
)

REM ===================================================================
REM Create Virtual Environment
REM ===================================================================

call :print_header "Setting Up Python Virtual Environment"

if exist ".venv" (
    call :print_warning "Virtual environment already exists"
    set /p "recreate=Do you want to recreate it? (y/N): "
    if /i "!recreate!"=="y" (
        call :print_info "Removing old virtual environment..."
        rmdir /s /q .venv
    ) else (
        call :print_info "Keeping existing virtual environment"
        goto :skip_venv_creation
    )
)

call :print_info "Creating virtual environment..."
%PYTHON_CMD% -m venv .venv

if %errorlevel% neq 0 (
    call :print_error "Failed to create virtual environment"
    pause
    exit /b 1
)

call :print_success "Virtual environment created"

:skip_venv_creation

REM ===================================================================
REM Activate Virtual Environment
REM ===================================================================

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
REM Install Python Dependencies
REM ===================================================================

call :print_header "Installing Python Dependencies"

call :print_info "Upgrading pip..."
python -m pip install --upgrade pip

if %errorlevel% neq 0 (
    call :print_warning "Failed to upgrade pip, continuing anyway..."
)

call :print_info "Installing requirements (this may take several minutes)..."
pip install -r requirements.txt

if %errorlevel% neq 0 (
    call :print_error "Failed to install Python dependencies"
    call :print_info "Check the error messages above for details"
    pause
    exit /b 1
)

call :print_success "Python dependencies installed"

REM ===================================================================
REM Setup Environment File
REM ===================================================================

call :print_header "Setting Up Environment Variables"

if exist ".env" (
    call :print_warning ".env file already exists"
    set /p "overwrite=Do you want to overwrite it? (y/N): "
    if /i not "!overwrite!"=="y" (
        call :print_info "Keeping existing .env file"
        goto :skip_env_creation
    )
)

call :print_info "Copying .env.example to .env..."
copy .env.example .env >nul

call :print_success ".env file created"
call :print_warning "IMPORTANT: Please edit .env and add your API keys!"

echo.
echo Required configuration:
echo   1. GOOGLE_API_KEY - Get from: https://makersuite.google.com/app/apikey
echo   2. JWT_SECRET_KEY - Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
echo   3. Database credentials (if using external database)
echo.

:skip_env_creation

REM ===================================================================
REM Create Project Directories
REM ===================================================================

call :print_header "Creating Project Directories"

call :print_info "Creating data directories..."

if not exist "data\faiss" mkdir data\faiss
if not exist "data\uploads" mkdir data\uploads
if not exist "logs" mkdir logs
if not exist "backups" mkdir backups

call :print_success "Directories created"

REM ===================================================================
REM Setup PostgreSQL with Docker
REM ===================================================================

call :print_header "Setting Up PostgreSQL Database"

where docker >nul 2>&1
if %errorlevel% neq 0 (
    call :print_warning "Docker not found. Skipping PostgreSQL setup"
    call :print_info "You'll need to install PostgreSQL manually or use Docker later"
    goto :skip_postgres_setup
)

set /p "start_postgres=Do you want to start PostgreSQL with Docker? (Y/n): "
if /i "!start_postgres!"=="n" (
    call :print_info "Skipping PostgreSQL setup"
    call :print_warning "Make sure you have PostgreSQL installed and running"
    goto :skip_postgres_setup
)

call :print_info "Starting PostgreSQL container..."

cd docker
docker-compose up -d postgres

if %errorlevel% neq 0 (
    call :print_error "Failed to start PostgreSQL container"
    cd ..
    goto :skip_postgres_setup
)

cd ..

call :print_success "PostgreSQL container started"
call :print_info "Waiting for PostgreSQL to be ready..."
timeout /t 5 /nobreak >nul

call :print_success "PostgreSQL is ready at localhost:5432"

:skip_postgres_setup

REM ===================================================================
REM Setup Tesseract OCR
REM ===================================================================

call :print_header "Checking Tesseract OCR"

where tesseract >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2" %%i in ('tesseract --version 2^>^&1 ^| findstr /C:"tesseract"') do set TESS_VERSION=%%i
    call :print_success "Tesseract found: !TESS_VERSION!"

    REM Check for Vietnamese language
    tesseract --list-langs 2>&1 | findstr /C:"vie" >nul
    if %errorlevel% equ 0 (
        call :print_success "Vietnamese language pack installed"
    ) else (
        call :print_warning "Vietnamese language pack not found"
        call :print_info "Download language packs from Tesseract installation"
    )
) else (
    call :print_warning "Tesseract OCR not found"
    call :print_info "Download from: https://github.com/UB-Mannheim/tesseract/wiki"
    call :print_info "After installation, add Tesseract to your PATH"
    call :print_info "Or disable OCR in .env: OCR_ENABLED=false"
)

REM ===================================================================
REM Initialize Database
REM ===================================================================

call :print_header "Initializing Database"

set /p "run_migrations=Do you want to run database migrations? (Y/n): "
if /i "!run_migrations!"=="n" (
    call :print_info "Skipping database migrations"
    goto :skip_migrations
)

if exist "alembic.ini" (
    call :print_info "Running Alembic migrations..."
    alembic upgrade head

    if %errorlevel% equ 0 (
        call :print_success "Database migrations completed"
    ) else (
        call :print_warning "Migration failed or not configured"
        call :print_info "Database tables will be created on first run"
    )
} else (
    call :print_warning "Alembic not configured. Skipping migrations"
    call :print_info "Database tables will be created on first run"
)

:skip_migrations

REM ===================================================================
REM Setup Frontend (Optional)
REM ===================================================================

call :print_header "Frontend Setup (Optional)"

if not exist "frontend\app" (
    call :print_info "Frontend directory not found. Skipping"
    goto :skip_frontend_setup
)

where node >nul 2>&1
if %errorlevel% neq 0 (
    call :print_warning "Node.js not found. Skipping frontend setup"
    goto :skip_frontend_setup
)

set /p "setup_frontend=Do you want to setup the frontend? (Y/n): "
if /i "!setup_frontend!"=="n" (
    call :print_info "Skipping frontend setup"
    goto :skip_frontend_setup
)

call :print_info "Installing frontend dependencies..."

cd frontend\app

if exist "package.json" (
    call npm install

    if %errorlevel% equ 0 (
        call :print_success "Frontend dependencies installed"
    ) else (
        call :print_error "Failed to install frontend dependencies"
    )
)

cd ..\..

:skip_frontend_setup

REM ===================================================================
REM Print Final Instructions
REM ===================================================================

call :print_header "Setup Complete!"

echo.
echo %GREEN%[+] Project setup completed successfully!%NC%
echo.
echo Next steps:
echo.
echo 1. Configure your environment:
echo    %YELLOW%notepad .env%NC%  (or your favorite editor)
echo.
echo 2. Start development server:
echo    %YELLOW%dev.bat%NC%
echo.
echo 3. Or start production server:
echo    %YELLOW%prod.bat start%NC%
echo.
echo 4. Access the application:
echo    API: %BLUE%http://localhost:8000%NC%
echo    Frontend: %BLUE%http://localhost:3000%NC%
echo    API Docs: %BLUE%http://localhost:8000/docs%NC%
echo.
echo %YELLOW%Important:%NC%
echo   - Edit %YELLOW%.env%NC% and add your GOOGLE_API_KEY
echo   - Ensure PostgreSQL is running (port 5432)
echo   - For OCR support, install Tesseract
echo.
echo Documentation:
echo   - User Guide: %BLUE%docs\RAG_ENHANCEMENTS_README.md%NC%
echo   - Shell Scripts: %BLUE%docs\SHELL_SCRIPTS_GUIDE.md%NC%
echo   - Implementation: %BLUE%docs\IMPLEMENTATION_SUMMARY.md%NC%
echo.

pause
exit /b 0