@echo off
REM Setup Official PhoGPT GGUF for Ollama (Docker Version)
REM For Ollama running in Docker container

setlocal enabledelayedexpansion

echo ==========================================
echo PhoGPT Official GGUF Setup (Docker)
echo ==========================================
echo.
echo This script will:
echo 1. Download official PhoGPT GGUF (2.36 GB)
echo 2. Copy to Docker container
echo 3. Create Ollama model in Docker
echo 4. Test the model
echo.

REM Configuration
set SCRIPT_DIR=%~dp0
set MODELS_DIR=%SCRIPT_DIR%models
set GGUF_FILE=phogpt-4b-chat-q4_k_m.gguf
set MODEL_NAME=phogpt-4b-chat
set CONTAINER_NAME=ollama
set DOCKER_MODEL_PATH=/root/.ollama/models

REM Check if Docker is running
echo Step 0: Checking Docker...
echo -----------------------------------

docker ps >nul 2>&1
if errorlevel 1 (
    echo Error: Docker is not running
    echo Please start Docker Desktop
    pause
    exit /b 1
)

echo OK: Docker is running

REM Check if Ollama container exists
docker ps | findstr /C:"%CONTAINER_NAME%" >nul
if errorlevel 1 (
    echo Error: Ollama container not found
    echo Please start Ollama container:
    echo   docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
    pause
    exit /b 1
)

echo OK: Ollama container is running

REM Create models directory
if not exist "%MODELS_DIR%" mkdir "%MODELS_DIR%"

echo.
echo Step 1: Checking prerequisites...
echo -----------------------------------

REM Check for huggingface-cli
huggingface-cli --version >nul 2>&1
if errorlevel 1 (
    echo huggingface-cli not found, installing...
    python -m pip install --upgrade pip
    pip install huggingface_hub

    REM Verify installation
    huggingface-cli --version >nul 2>&1
    if errorlevel 1 (
        echo Error: Failed to install huggingface_hub
        echo.
        echo Please install manually:
        echo   pip install huggingface_hub
        echo.
        pause
        exit /b 1
    )
    echo OK: huggingface-cli installed
) else (
    echo OK: huggingface-cli found
)

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
echo Step 3: Copying GGUF to Docker container...
echo -----------------------------------

REM Copy GGUF file to Docker container's temp directory
docker cp "%GGUF_FILE%" %CONTAINER_NAME%:/tmp/%GGUF_FILE%
if errorlevel 1 (
    echo Error: Failed to copy file to Docker container
    pause
    exit /b 1
)

echo OK: File copied to container

echo.
echo Step 4: Creating Modelfile in container...
echo -----------------------------------

REM Create Modelfile content
set MODELFILE_CONTENT=FROM /tmp/%GGUF_FILE%^

^

PARAMETER temperature 0.7^

PARAMETER top_p 0.9^

PARAMETER top_k 50^

PARAMETER num_ctx 4096^

PARAMETER num_predict 2048^

PARAMETER stop "### Câu hỏi:"^

PARAMETER stop "<|endoftext|>"^

^

SYSTEM """Bạn là trợ lý AI chuyên nghiệp về tìm kiếm việc làm và tư vấn nghề nghiệp tại Việt Nam.^

^

Nhiệm vụ của bạn:^

1. Hiểu và phân tích yêu cầu tìm việc của người dùng^

2. Sử dụng các công cụ (tools) để tìm kiếm việc làm phù hợp^

3. Trả lời bằng tiếng Việt tự nhiên, chuyên nghiệp và thân thiện^

4. Cung cấp thông tin chính xác, cụ thể về công việc^

^

Khi người dùng hỏi về việc làm:^

- Luôn sử dụng công cụ job_search để tìm kiếm^

- Trích xuất từ khóa chính xác (vị trí, địa điểm, ngành nghề)^

- Tổng hợp kết quả một cách rõ ràng, dễ hiểu"""^

^

TEMPLATE """### Câu hỏi: {{ .Prompt }}^

### Trả lời:"""^

^

MESSAGE system """{{ .System }}"""^

MESSAGE user """### Câu hỏi: {{ .Content }}"""^

MESSAGE assistant """### Trả lời: {{ .Content }}"""

REM Write Modelfile to container
echo !MODELFILE_CONTENT! | docker exec -i %CONTAINER_NAME% sh -c "cat > /tmp/Modelfile.phogpt"

echo OK: Modelfile created in container

echo.
echo Step 5: Creating Ollama model in Docker...
echo -----------------------------------
echo Model name: %MODEL_NAME%
echo This may take 1-2 minutes...

REM Create model inside container
docker exec %CONTAINER_NAME% ollama create %MODEL_NAME% -f /tmp/Modelfile.phogpt
if errorlevel 1 (
    echo Error: Failed to create Ollama model
    pause
    exit /b 1
)

echo OK: Model created successfully

echo.
echo Step 6: Verifying model...
echo -----------------------------------

docker exec %CONTAINER_NAME% ollama list | findstr /C:"%MODEL_NAME%"
if errorlevel 1 (
    echo Warning: Model not found in Ollama list
) else (
    echo OK: Model verified in Ollama
)

echo.
echo Step 7: Testing model...
echo -----------------------------------
echo Running test query...
echo.

docker exec -i %CONTAINER_NAME% ollama run %MODEL_NAME% "Xin chào, bạn có thể giúp tôi tìm việc làm không?"

echo.
echo Step 8: Cleanup temp files in container...
echo -----------------------------------

docker exec %CONTAINER_NAME% sh -c "rm -f /tmp/%GGUF_FILE% /tmp/Modelfile.phogpt"
echo OK: Cleanup complete

echo.
echo ==========================================
echo Setup Complete!
echo ==========================================
echo.
echo Your PhoGPT model is ready: %MODEL_NAME%
echo Running in Docker container: %CONTAINER_NAME%
echo.
echo Docker Info:
docker exec %CONTAINER_NAME% ollama list | findstr /C:"%MODEL_NAME%"
echo.
echo Next steps:
echo 1. Update your .env file:
echo    LLM_MODEL=%MODEL_NAME%
echo    QWEN_MODEL=%MODEL_NAME%
echo    OLLAMA_HOST=http://localhost:11434
echo.
echo 2. Restart your job_bot service:
echo    python job_bot\main.py
echo.
echo 3. Test the integration:
echo    curl -X POST http://localhost:11434/api/chat -d "{\"model\":\"%MODEL_NAME%\",\"messages\":[{\"role\":\"user\",\"content\":\"Xin chào\"}]}"
echo.
echo ==========================================

pause
