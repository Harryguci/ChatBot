@echo off
REM Simple download script for PhoGPT GGUF
REM Uses curl or PowerShell to download directly from Hugging Face

setlocal enabledelayedexpansion

echo ==========================================
echo PhoGPT GGUF Download
echo ==========================================

set MODELS_DIR=%~dp0models
set GGUF_FILE=phogpt-4b-chat-q4_k_m.gguf
set DOWNLOAD_URL=https://huggingface.co/vinai/PhoGPT-4B-Chat-gguf/resolve/main/phogpt-4b-chat-q4_k_m.gguf

REM Create models directory
if not exist "%MODELS_DIR%" mkdir "%MODELS_DIR%"

cd /d "%MODELS_DIR%"

REM Check if file already exists
if exist "%GGUF_FILE%" (
    echo File already exists: %GGUF_FILE%
    echo Size:
    dir "%GGUF_FILE%" | findstr /C:".gguf"
    echo.
    choice /C YN /M "Re-download anyway"
    if errorlevel 2 (
        echo Skipping download
        goto :verify
    )
)

echo.
echo Downloading PhoGPT GGUF...
echo Source: %DOWNLOAD_URL%
echo Target: %MODELS_DIR%\%GGUF_FILE%
echo Size: 2.36 GB
echo This may take 10-20 minutes...
echo.

REM Try curl first (faster, shows progress)
curl --version >nul 2>&1
if not errorlevel 1 (
    echo Using curl...
    curl -L -o "%GGUF_FILE%" "%DOWNLOAD_URL%"
    goto :check_download
)

REM Fallback to PowerShell
echo Using PowerShell...
powershell -Command "& {$ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri '%DOWNLOAD_URL%' -OutFile '%GGUF_FILE%'}"

:check_download
if not exist "%GGUF_FILE%" (
    echo.
    echo Error: Download failed
    echo.
    echo Please try manual download:
    echo 1. Open in browser: https://huggingface.co/vinai/PhoGPT-4B-Chat-gguf/tree/main
    echo 2. Click on: phogpt-4b-chat-q4_k_m.gguf
    echo 3. Click "download" button
    echo 4. Move file to: %MODELS_DIR%
    echo.
    pause
    exit /b 1
)

:verify
echo.
echo ==========================================
echo Download Complete!
echo ==========================================
echo.
echo File: %GGUF_FILE%
dir "%GGUF_FILE%" | findstr /C:".gguf"
echo.
echo Location: %MODELS_DIR%
echo.
echo Next step: Run setup script
echo   - For Docker: setup_phogpt_docker.bat
echo   - For Host:   setup_phogpt_official.bat
echo.
pause
