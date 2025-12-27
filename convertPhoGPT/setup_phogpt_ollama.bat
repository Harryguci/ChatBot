@echo off
REM Quick setup script for PhoGPT in Ollama (Windows)
REM This assumes you already have the GGUF file converted

setlocal enabledelayedexpansion

echo ==========================================
echo PhoGPT Ollama Setup (Windows)
echo ==========================================

REM Default GGUF path (relative to convertPhoGPT folder)
set DEFAULT_GGUF=%~dp0phogpt_conversion\models\phogpt-4b-chat-q4_k_m.gguf
set MODEL_NAME=phogpt-4b-chat
set MODELFILE=%~dp0..\job_bot\Modelfile.phogpt

echo.
echo Checking for GGUF file...

REM Check if GGUF exists
if exist "%DEFAULT_GGUF%" (
    set GGUF_PATH=%DEFAULT_GGUF%
    echo OK: Found %GGUF_PATH%
) else (
    echo GGUF file not found at default location: %DEFAULT_GGUF%
    echo.
    set /p GGUF_PATH="Enter path to your PhoGPT GGUF file: "

    if not exist "!GGUF_PATH!" (
        echo Error: File not found: !GGUF_PATH!
        exit /b 1
    )
)

echo.
echo Creating temporary Modelfile...

REM Create temporary Modelfile with correct path
set TEMP_MODELFILE=%TEMP%\Modelfile.phogpt.tmp

(
echo # Modelfile for PhoGPT-4B-Chat
echo FROM !GGUF_PATH!
echo.
echo # Model parameters optimized for Vietnamese job search chatbot
echo PARAMETER temperature 0.7
echo PARAMETER top_p 0.9
echo PARAMETER top_k 50
echo PARAMETER num_ctx 4096
echo PARAMETER num_predict 2048
echo PARAMETER stop "### Câu hỏi:"
echo PARAMETER stop "^<^|endoftext^|^>"
echo PARAMETER stop "^</s^>"
echo.
echo # System prompt for job search domain
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
echo - Tổng hợp kết quả một cách rõ ràng, dễ hiểu
echo.
echo Phong cách giao tiếp:
echo - Lịch sự, thân thiện nhưng chuyên nghiệp
echo - Ngắn gọn, súc tích, đi thẳng vào vấn đề
echo - Sử dụng tiếng Việt chuẩn, tránh lỗi chính tả
echo """
echo.
echo # Template for PhoGPT prompt format
echo TEMPLATE """### Câu hỏi: {{ .Prompt }}
echo ### Trả lời:"""
echo.
echo MESSAGE system """{{ .System }}"""
echo MESSAGE user """### Câu hỏi: {{ .Content }}"""
echo MESSAGE assistant """### Trả lời: {{ .Content }}"""
) > "%TEMP_MODELFILE%"

echo OK: Modelfile created at %TEMP_MODELFILE%

echo.
echo Checking Ollama...

REM Check if Ollama is installed
ollama --version >nul 2>&1
if errorlevel 1 (
    echo Error: Ollama is not installed or not in PATH
    echo Install from: https://ollama.ai
    exit /b 1
)

REM Test Ollama connection
ollama list >nul 2>&1
if errorlevel 1 (
    echo Error: Ollama service is not running
    echo Start it with: ollama serve
    exit /b 1
)

echo OK: Ollama is running

echo.
echo Creating Ollama model: %MODEL_NAME%
echo This may take a few minutes...

REM Create the model
ollama create %MODEL_NAME% -f "%TEMP_MODELFILE%"

if errorlevel 1 (
    echo Error: Model creation failed
    del "%TEMP_MODELFILE%"
    exit /b 1
)

echo.
echo Verifying model...

REM Check if model was created
ollama list | findstr /C:"%MODEL_NAME%" >nul
if errorlevel 1 (
    echo Error: Model not found in Ollama list
    del "%TEMP_MODELFILE%"
    exit /b 1
)

echo OK: Model created successfully

REM Clean up
del "%TEMP_MODELFILE%"

echo.
echo Testing model...
echo -----------------------------------

REM Test the model
ollama run %MODEL_NAME% "Xin chào, bạn là ai?"

echo.
echo ==========================================
echo Setup Complete!
echo ==========================================
echo.
echo Model '%MODEL_NAME%' is ready to use.
echo.
echo Next steps:
echo 1. Update your .env file:
echo    LLM_MODEL=%MODEL_NAME%
echo.
echo 2. Restart your job_bot service
echo.
echo 3. Test the integration:
echo    curl -X POST http://localhost:8000/chat ^
echo      -H "Content-Type: application/json" ^
echo      -d "{\"user_id\":\"test\",\"message\":\"Tìm việc kỹ sư phần mềm\"}"
echo.
echo ==========================================

pause
