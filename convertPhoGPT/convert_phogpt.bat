@echo off
REM Script to convert PhoGPT-4B-Chat to GGUF format for Ollama (Windows)
REM This version automatically creates and uses a virtual environment
REM Usage: convert_phogpt.bat

setlocal enabledelayedexpansion

echo ==========================================
echo PhoGPT to GGUF Conversion Script (Windows)
echo With Automatic Virtual Environment
echo ==========================================

REM Configuration
set PHOGPT_MODEL=vinai/PhoGPT-4B-Chat
set SCRIPT_DIR=%~dp0
set WORK_DIR=%SCRIPT_DIR%phogpt_conversion
set VENV_DIR=%WORK_DIR%\venv_conversion
set LLAMA_CPP_DIR=%WORK_DIR%\llama.cpp
set MODELS_DIR=%WORK_DIR%\models
set HF_MODEL_DIR=%MODELS_DIR%\phogpt-4b-chat-hf
set OUTPUT_GGUF=%MODELS_DIR%\phogpt-4b-chat.gguf
set QUANTIZED_GGUF=%MODELS_DIR%\phogpt-4b-chat-q4_k_m.gguf

REM Create working directory
if not exist "%WORK_DIR%" mkdir "%WORK_DIR%"
if not exist "%MODELS_DIR%" mkdir "%MODELS_DIR%"

echo.
echo Step 1: Checking prerequisites...
echo -----------------------------------

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python 3 is not installed
    echo Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)

echo OK: Python found

REM Get Python version for display
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo    Version: %PYTHON_VERSION%

REM Check for git
git --version >nul 2>&1
if errorlevel 1 (
    echo Error: git is not installed
    echo Please install git from https://git-scm.com/
    pause
    exit /b 1
)

echo OK: git found

echo.
echo Step 2: Setting up virtual environment...
echo -----------------------------------

REM Create virtual environment if it doesn't exist
if not exist "%VENV_DIR%" (
    echo Creating new virtual environment at %VENV_DIR%
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo Error: Failed to create virtual environment
        echo Make sure Python venv module is installed
        pause
        exit /b 1
    )
    echo OK: Virtual environment created
) else (
    echo OK: Virtual environment already exists
)

REM Activate virtual environment
echo Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo Error: Failed to activate virtual environment
    pause
    exit /b 1
)

echo OK: Virtual environment activated
echo    Python: %VIRTUAL_ENV%

REM Upgrade pip in venv
echo Upgrading pip in virtual environment...
python -m pip install --upgrade pip --quiet

echo.
echo Step 3: Installing Python dependencies in venv...
echo -----------------------------------

REM Install huggingface-cli first
echo Installing huggingface_hub...
pip install huggingface_hub[cli] --quiet
if errorlevel 1 (
    echo Warning: Failed to install huggingface_hub
)

REM Install conversion dependencies
echo Installing torch, transformers, sentencepiece, protobuf...
pip install torch transformers sentencepiece protobuf --quiet
if errorlevel 1 (
    echo Error: Failed to install conversion dependencies
    pause
    exit /b 1
)

echo OK: Dependencies installed in virtual environment

echo.
echo Step 4: Cloning llama.cpp...
echo -----------------------------------

if not exist "%LLAMA_CPP_DIR%" (
    git clone https://github.com/ggerganov/llama.cpp "%LLAMA_CPP_DIR%"
    if errorlevel 1 (
        echo Error: Failed to clone llama.cpp
        pause
        exit /b 1
    )
) else (
    echo llama.cpp already exists, pulling latest...
    cd /d "%LLAMA_CPP_DIR%"
    git pull
)

echo OK: llama.cpp ready

echo.
echo Step 5: Installing llama.cpp Python dependencies...
echo -----------------------------------

cd /d "%LLAMA_CPP_DIR%"
if exist "requirements.txt" (
    echo Installing from llama.cpp requirements.txt...
    pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo Warning: Some requirements may have failed to install
    )
)

echo OK: llama.cpp dependencies installed

echo.
echo Step 6: Downloading PhoGPT from Hugging Face...
echo -----------------------------------

cd /d "%WORK_DIR%"

if not exist "%HF_MODEL_DIR%" (
    echo Downloading %PHOGPT_MODEL%...
    echo This may take 10-20 minutes depending on your internet speed...
    huggingface-cli download %PHOGPT_MODEL% --local-dir "%HF_MODEL_DIR%"
    if errorlevel 1 (
        echo Error: Failed to download PhoGPT model
        echo Please check your internet connection and try again
        pause
        exit /b 1
    )
) else (
    echo Model already downloaded at %HF_MODEL_DIR%
)

echo OK: PhoGPT downloaded

echo.
echo Step 7: Converting to GGUF (FP16)...
echo -----------------------------------

cd /d "%LLAMA_CPP_DIR%"

if not exist "%OUTPUT_GGUF%" (
    echo Converting PhoGPT to GGUF format...
    echo This may take 5-10 minutes...

    REM Try new converter first (convert_hf_to_gguf.py)
    if exist "convert_hf_to_gguf.py" (
        echo Using convert_hf_to_gguf.py...
        python convert_hf_to_gguf.py "%HF_MODEL_DIR%" --outfile "%OUTPUT_GGUF%" --outtype f16
    ) else if exist "convert.py" (
        echo Using convert.py...
        python convert.py "%HF_MODEL_DIR%" --outfile "%OUTPUT_GGUF%" --outtype f16
    ) else (
        echo Error: No conversion script found (convert_hf_to_gguf.py or convert.py)
        pause
        exit /b 1
    )

    if errorlevel 1 (
        echo Error: Conversion to GGUF failed
        pause
        exit /b 1
    )
    echo OK: Converted to GGUF (FP16)
) else (
    echo GGUF file already exists: %OUTPUT_GGUF%
)

echo.
echo Step 8: Checking for quantize tool...
echo -----------------------------------

REM For Windows, you need to build with CMake or use pre-built binaries
if not exist "quantize.exe" (
    echo.
    echo NOTE: quantize.exe not found
    echo.
    echo To quantize the model (reduce size from ~8GB to ~2.5GB), you need quantize.exe
    echo.
    echo Option 1: Build from source (requires CMake and Visual Studio Build Tools)
    echo   1. Install CMake: https://cmake.org/download/
    echo   2. Install Visual Studio Build Tools
    echo   3. Run: cmake -B build
    echo   4. Run: cmake --build build --config Release
    echo   5. Copy build\bin\Release\quantize.exe to %LLAMA_CPP_DIR%
    echo.
    echo Option 2: Download pre-built binaries
    echo   https://github.com/ggerganov/llama.cpp/releases
    echo   Download and extract quantize.exe to %LLAMA_CPP_DIR%
    echo.
    echo You can use the FP16 GGUF file as-is (larger but works), or quantize later.
    echo.
    choice /C YN /M "Skip quantization and continue"
    if errorlevel 2 (
        echo Exiting...
        pause
        exit /b 0
    )
    goto :skip_quantize
)

echo OK: quantize.exe found

echo.
echo Step 9: Quantizing to Q4_K_M (recommended)...
echo -----------------------------------

if not exist "%QUANTIZED_GGUF%" (
    echo Quantizing model to reduce size...
    echo This may take 2-5 minutes...
    quantize.exe "%OUTPUT_GGUF%" "%QUANTIZED_GGUF%" q4_k_m
    if errorlevel 1 (
        echo Warning: Quantization failed
        echo You can still use the FP16 version: %OUTPUT_GGUF%
        goto :skip_quantize
    )
    echo OK: Quantized to Q4_K_M
) else (
    echo Quantized file already exists: %QUANTIZED_GGUF%
)

:skip_quantize

echo.
echo Step 10: Model file information...
echo -----------------------------------

echo Original GGUF (FP16):
if exist "%OUTPUT_GGUF%" (
    dir "%OUTPUT_GGUF%" | findstr /C:".gguf"
) else (
    echo    Not found
)

if exist "%QUANTIZED_GGUF%" (
    echo.
    echo Quantized GGUF (Q4_K_M):
    dir "%QUANTIZED_GGUF%" | findstr /C:".gguf"
)

REM Deactivate virtual environment
echo.
echo Deactivating virtual environment...
call deactivate 2>nul

echo.
echo ==========================================
echo Conversion Process Completed!
echo ==========================================
echo.
echo Your converted model files are located at:
echo   FP16:    %OUTPUT_GGUF%
if exist "%QUANTIZED_GGUF%" (
    echo   Q4_K_M:  %QUANTIZED_GGUF% (RECOMMENDED)
)
echo.
echo Virtual environment is at:
echo   %VENV_DIR%
echo   (You can delete this folder after creating the Ollama model)
echo.
echo ==========================================
echo Next Steps:
echo ==========================================
echo.
echo 1. Update ..\job_bot\Modelfile.phogpt with the correct path:
if exist "%QUANTIZED_GGUF%" (
    echo    FROM %QUANTIZED_GGUF%
) else (
    echo    FROM %OUTPUT_GGUF%
)
echo.
echo 2. Create Ollama model:
echo    cd ..\job_bot
echo    ollama create phogpt-4b-chat -f Modelfile.phogpt
echo.
echo    OR use the quick setup script:
echo    cd ..\convertPhoGPT
echo    setup_phogpt_ollama.bat
echo.
echo 3. Test the model:
echo    ollama run phogpt-4b-chat "Xin chào, bạn có thể giúp tôi tìm việc làm không?"
echo.
echo 4. Update your .env file:
echo    LLM_MODEL=phogpt-4b-chat
echo.
echo ==========================================

pause
