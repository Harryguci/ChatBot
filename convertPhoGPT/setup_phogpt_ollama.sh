#!/bin/bash
# Quick setup script for PhoGPT in Ollama
# This assumes you already have the GGUF file converted

set -e

echo "=========================================="
echo "PhoGPT Ollama Setup"
echo "=========================================="

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default GGUF path (relative to convertPhoGPT folder)
DEFAULT_GGUF="${SCRIPT_DIR}/phogpt_conversion/models/phogpt-4b-chat-q4_k_m.gguf"
MODEL_NAME="phogpt-4b-chat"
MODELFILE="${SCRIPT_DIR}/../job_bot/Modelfile.phogpt"

echo ""
echo "Checking for GGUF file..."

# Check if GGUF exists
if [ -f "$DEFAULT_GGUF" ]; then
    GGUF_PATH="$DEFAULT_GGUF"
    echo "✓ Found: $GGUF_PATH"
else
    echo "GGUF file not found at default location: $DEFAULT_GGUF"
    echo ""
    read -p "Enter path to your PhoGPT GGUF file: " GGUF_PATH

    if [ ! -f "$GGUF_PATH" ]; then
        echo "Error: File not found: $GGUF_PATH"
        exit 1
    fi
fi

echo ""
echo "Creating temporary Modelfile..."

# Create temporary Modelfile with correct path
TEMP_MODELFILE="/tmp/Modelfile.phogpt.tmp"
cat > "$TEMP_MODELFILE" << EOF
# Modelfile for PhoGPT-4B-Chat
FROM $GGUF_PATH

# Model parameters optimized for Vietnamese job search chatbot
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 50
PARAMETER num_ctx 4096
PARAMETER num_predict 2048
PARAMETER stop "### Câu hỏi:"
PARAMETER stop "<|endoftext|>"
PARAMETER stop "</s>"

# System prompt for job search domain
SYSTEM """Bạn là trợ lý AI chuyên nghiệp về tìm kiếm việc làm và tư vấn nghề nghiệp tại Việt Nam.

Nhiệm vụ của bạn:
1. Hiểu và phân tích yêu cầu tìm việc của người dùng
2. Sử dụng các công cụ (tools) để tìm kiếm việc làm phù hợp
3. Trả lời bằng tiếng Việt tự nhiên, chuyên nghiệp và thân thiện
4. Cung cấp thông tin chính xác, cụ thể về công việc

Khi người dùng hỏi về việc làm:
- Luôn sử dụng công cụ job_search để tìm kiếm
- Trích xuất từ khóa chính xác (vị trí, địa điểm, ngành nghề)
- Tổng hợp kết quả một cách rõ ràng, dễ hiểu

Phong cách giao tiếp:
- Lịch sự, thân thiện nhưng chuyên nghiệp
- Ngắn gọn, súc tích, đi thẳng vào vấn đề
- Sử dụng tiếng Việt chuẩn, tránh lỗi chính tả
"""

# Template for PhoGPT prompt format
TEMPLATE """### Câu hỏi: {{ .Prompt }}
### Trả lời:"""

MESSAGE system """{{ .System }}"""
MESSAGE user """### Câu hỏi: {{ .Content }}"""
MESSAGE assistant """### Trả lời: {{ .Content }}"""
EOF

echo "✓ Modelfile created"

echo ""
echo "Checking Ollama..."

# Check if Ollama is running
if ! command -v ollama &> /dev/null; then
    echo "Error: Ollama is not installed or not in PATH"
    echo "Install from: https://ollama.ai"
    exit 1
fi

# Test Ollama connection
if ! ollama list &> /dev/null; then
    echo "Error: Ollama service is not running"
    echo "Start it with: ollama serve"
    exit 1
fi

echo "✓ Ollama is running"

echo ""
echo "Creating Ollama model: $MODEL_NAME"
echo "This may take a few minutes..."

# Create the model
ollama create "$MODEL_NAME" -f "$TEMP_MODELFILE"

echo ""
echo "Verifying model..."

# Check if model was created
if ollama list | grep -q "$MODEL_NAME"; then
    echo "✓ Model created successfully"
else
    echo "Error: Model creation failed"
    exit 1
fi

# Clean up
rm "$TEMP_MODELFILE"

echo ""
echo "Testing model..."
echo "-----------------------------------"

# Test the model
ollama run "$MODEL_NAME" "Xin chào, bạn là ai?" --verbose 2>&1 | head -n 20

echo ""
echo "=========================================="
echo "✓ Setup Complete!"
echo "=========================================="
echo ""
echo "Model '$MODEL_NAME' is ready to use."
echo ""
echo "Next steps:"
echo "1. Update your .env file:"
echo "   LLM_MODEL=$MODEL_NAME"
echo ""
echo "2. Restart your job_bot service"
echo ""
echo "3. Test the integration:"
echo "   curl -X POST http://localhost:8000/chat \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"user_id\":\"test\",\"message\":\"Tìm việc kỹ sư phần mềm\"}'"
echo ""
echo "=========================================="
