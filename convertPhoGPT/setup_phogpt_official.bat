@echo off
REM Setup Official PhoGPT GGUF for Ollama
REM No conversion needed - uses pre-made GGUF files

setlocal enabledelayedexpansion

echo ==========================================
echo PhoGPT Official GGUF Setup
echo ==========================================
echo.
echo This script will:
echo 1. Download official PhoGPT GGUF (2.36 GB)
echo 2. Create Ollama model
echo 3. Test the model
echo.
pause

REM Configuration
set SCRIPT_DIR=%~dp0
set MODELS_DIR=%SCRIPT_DIR%models
set GGUF_FILE=phogpt-4b-chat-q4_k_m.gguf
set MODEL_NAME=phogpt-4b-chat
set MODELFILE=%SCRIPT_DIR%..\job_bot\Modelfile.phogpt

REM Create models directory
if not exist "%MODELS_DIR%" mkdir "%MODELS_DIR%"

echo.
echo Step 1: Checking prerequisites...
echo -----------------------------------

REM Check for huggingface-cli
huggingface-cli --version >nul 2>&1
if errorlevel 1 (
    echo Installing huggingface_hub[cli]...
    pip install "huggingface_hub[cli]"
    if errorlevel 1 (
        echo Error: Failed to install huggingface_hub
        pause
        exit /b 1
    )
)

echo OK: huggingface-cli found

REM Check for ollama
ollama --version >nul 2>&1
if errorlevel 1 (
    echo Error: Ollama is not installed
    echo Please install from: https://ollama.ai
    pause
    exit /b 1
)

echo OK: Ollama found

echo.
echo Step 2: Downloading PhoGPT GGUF...
echo -----------------------------------
echo Source: https://huggingface.co/vinai/PhoGPT-4B-Chat-gguf
echo File: %GGUF_FILE% (2.36 GB)
echo This may take 5-10 minutes...
echo.

cd /d "%MODELS_DIR%"

if not exist "%GGUF_FILE%" (
    huggingface-cli download vinai/PhoGPT-4B-Chat-gguf %GGUF_FILE% --local-dir .
    if errorlevel 1 (
        echo.
        echo Error: Download failed
        echo.
        echo Try manual download:
        echo 1. Go to: https://huggingface.co/vinai/PhoGPT-4B-Chat-gguf/tree/main
        echo 2. Download: %GGUF_FILE%
        echo 3. Save to: %MODELS_DIR%
        echo 4. Run this script again
        pause
        exit /b 1
    )
    echo OK: Downloaded successfully
) else (
    echo OK: GGUF file already exists
)

echo.
echo Step 3: Creating Modelfile...
echo -----------------------------------

REM Create Modelfile if it doesn't exist
if not exist "%MODELFILE%" (
    echo Creating new Modelfile at: %MODELFILE%

    (
    echo # Official PhoGPT 4B Chat GGUF
    echo FROM %MODELS_DIR%\%GGUF_FILE%
    echo.
    echo # Optimized parameters for Vietnamese job search
    echo PARAMETER temperature 0.7
    echo PARAMETER top_p 0.9
    echo PARAMETER top_k 50
    echo PARAMETER num_ctx 4096
    echo PARAMETER num_predict 2048
    echo PARAMETER stop "### Câu hỏi:"
    echo PARAMETER stop "^<^|endoftext^|^>"
    echo.
    echo # System prompt for job search
    echo SYSTEM """Bạn là trợ lý AI chuyên nghiệp về tìm kiếm việc làm và tư vấn nghề nghiệp tại Việt Nam.
    echo.
    echo Nhiệm vụ của bạn:
    echo 1. Hiểu và phân tích yêu cầu tìm việc của người dùng
    echo 2. Sử dụng các công cụ ^(tools^) để tìm kiếm việc làm phù hợp
    echo 3. Trả lời bằng tiếng Việt tự nhiên, chuyên nghiệp và thân thiện
    echo 4. Cung cấp thông tin chính xác, cụ thể về công việc
    echo.
    echo Khi người dùng hỏi về việc làm:
    echo - Luôn sử dụng công cụ job_search để tìm kiếm
    echo - Trích xuất từ khóa chính xác ^(vị trí, địa điểm, ngành nghề^)
    echo - Tổng hợp kết quả một cách rõ ràng, dễ hiểu"""
    echo.
    echo # PhoGPT prompt template
    echo TEMPLATE """### Câu hỏi: {{ .Prompt }}
    echo ### Trả lời:"""
    echo.
    echo MESSAGE system """{{ .System }}"""
    echo MESSAGE user """### Câu hỏi: {{ .Content }}"""
    echo MESSAGE assistant """### Trả lời: {{ .Content }}"""
    ) > "%MODELFILE%"

    echo OK: Modelfile created
) else (
    echo OK: Modelfile already exists
)

echo.
echo Step 4: Creating Ollama model...
echo -----------------------------------
echo Model name: %MODEL_NAME%
echo This may take 1-2 minutes...

ollama create %MODEL_NAME% -f "%MODELFILE%"
if errorlevel 1 (
    echo Error: Failed to create Ollama model
    pause
    exit /b 1
)

echo OK: Model created successfully

echo.
echo Step 5: Verifying model...
echo -----------------------------------

ollama list | findstr /C:"%MODEL_NAME%" >nul
if errorlevel 1 (
    echo Warning: Model not found in Ollama list
    echo Run: ollama list
) else (
    echo OK: Model verified in Ollama
)

echo.
echo Step 6: Testing model...
echo -----------------------------------
echo Running test query...
echo.

ollama run %MODEL_NAME% "Xin chào, bạn có thể giúp tôi tìm việc làm không?"

echo.
echo ==========================================
echo Setup Complete!
echo ==========================================
echo.
echo Your PhoGPT model is ready: %MODEL_NAME%
echo.
echo Next steps:
echo 1. Update your .env file:
echo    LLM_MODEL=%MODEL_NAME%
echo    QWEN_MODEL=%MODEL_NAME%
echo.
echo 2. Restart your job_bot service:
echo    python job_bot\main.py
echo.
echo 3. Test the integration:
echo    python job_bot\test_phogpt.py
echo.
echo ==========================================

pause
