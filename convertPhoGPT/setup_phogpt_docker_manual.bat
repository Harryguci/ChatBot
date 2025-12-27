@echo off
REM Setup PhoGPT GGUF for Ollama (Docker) - Manual Download Version
REM Use this after manually downloading the GGUF file

setlocal enabledelayedexpansion

echo ==========================================
echo PhoGPT Docker Setup (Manual Download)
echo ==========================================
echo.

REM Configuration
set SCRIPT_DIR=%~dp0
set MODELS_DIR=%SCRIPT_DIR%models
set GGUF_FILE=phogpt-4b-chat-q4_k_m.gguf
set MODEL_NAME=phogpt-4b-chat
set CONTAINER_NAME=ollama

REM Check if Docker is running
echo Step 1: Checking Docker...
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

echo.
echo Step 2: Checking GGUF file...
echo -----------------------------------

cd /d "%MODELS_DIR%"

if not exist "%GGUF_FILE%" (
    echo Error: GGUF file not found
    echo Expected: %MODELS_DIR%\%GGUF_FILE%
    echo.
    echo Please download the file first:
    echo   powershell -ExecutionPolicy Bypass -File ..\download_gguf.ps1
    echo.
    pause
    exit /b 1
)

echo OK: GGUF file found
echo File size:
dir "%GGUF_FILE%" | findstr /C:".gguf"

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

REM Create Modelfile content using echo and pipe to docker
(
echo FROM /tmp/%GGUF_FILE%
echo.
echo PARAMETER temperature 0.7
echo PARAMETER top_p 0.9
echo PARAMETER top_k 50
echo PARAMETER num_ctx 8192
echo PARAMETER num_predict 4096
echo PARAMETER stop "### Câu hỏi:"
echo PARAMETER stop "^<^|endoftext^|^>"
echo.
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
echo TEMPLATE """### Câu hỏi: {{ .Prompt }}
echo ### Trả lời:"""
echo.
echo MESSAGE system """{{ .System }}"""
echo MESSAGE user """### Câu hỏi: {{ .Prompt }}"""
echo MESSAGE assistant """### Trả lời: """
) | docker exec -i %CONTAINER_NAME% sh -c "cat > /tmp/Modelfile.phogpt"

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
