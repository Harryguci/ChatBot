#!/bin/bash
# Setup Official PhoGPT GGUF for Ollama
# No conversion needed - uses pre-made GGUF files

set -e

echo "=========================================="
echo "PhoGPT Official GGUF Setup"
echo "=========================================="
echo ""
echo "This script will:"
echo "1. Download official PhoGPT GGUF (2.36 GB)"
echo "2. Create Ollama model"
echo "3. Test the model"
echo ""
read -p "Press Enter to continue..."

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELS_DIR="${SCRIPT_DIR}/models"
GGUF_FILE="phogpt-4b-chat-q4_k_m.gguf"
MODEL_NAME="phogpt-4b-chat"
MODELFILE="${SCRIPT_DIR}/../job_bot/Modelfile.phogpt"

# Create models directory
mkdir -p "${MODELS_DIR}"

echo ""
echo "Step 1: Checking prerequisites..."
echo "-----------------------------------"

# Check for huggingface-cli
if ! command -v huggingface-cli &> /dev/null; then
    echo "Installing huggingface_hub[cli]..."
    pip install "huggingface_hub[cli]"
fi

echo "✓ huggingface-cli found"

# Check for ollama
if ! command -v ollama &> /dev/null; then
    echo "Error: Ollama is not installed"
    echo "Please install from: https://ollama.ai"
    exit 1
fi

echo "✓ Ollama found"

echo ""
echo "Step 2: Downloading PhoGPT GGUF..."
echo "-----------------------------------"
echo "Source: https://huggingface.co/vinai/PhoGPT-4B-Chat-gguf"
echo "File: ${GGUF_FILE} (2.36 GB)"
echo "This may take 5-10 minutes..."
echo ""

cd "${MODELS_DIR}"

if [ ! -f "${GGUF_FILE}" ]; then
    huggingface-cli download vinai/PhoGPT-4B-Chat-gguf "${GGUF_FILE}" --local-dir .
    echo "✓ Downloaded successfully"
else
    echo "✓ GGUF file already exists"
fi

echo ""
echo "Step 3: Creating Modelfile..."
echo "-----------------------------------"

# Create Modelfile if it doesn't exist
if [ ! -f "${MODELFILE}" ]; then
    echo "Creating new Modelfile at: ${MODELFILE}"

    cat > "${MODELFILE}" << 'EOF'
# Official PhoGPT 4B Chat GGUF
FROM ../convertPhoGPT/models/phogpt-4b-chat-q4_k_m.gguf

# Optimized parameters for Vietnamese job search
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 50
PARAMETER num_ctx 4096
PARAMETER num_predict 2048
PARAMETER stop "### Câu hỏi:"
PARAMETER stop "<|endoftext|>"

# System prompt for job search
SYSTEM """Bạn là trợ lý AI chuyên nghiệp về tìm kiếm việc làm và tư vấn nghề nghiệp tại Việt Nam.

Nhiệm vụ của bạn:
1. Hiểu và phân tích yêu cầu tìm việc của người dùng
2. Sử dụng các công cụ (tools) để tìm kiếm việc làm phù hợp
3. Trả lời bằng tiếng Việt tự nhiên, chuyên nghiệp và thân thiện
4. Cung cấp thông tin chính xác, cụ thể về công việc

Khi người dùng hỏi về việc làm:
- Luôn sử dụng công cụ job_search để tìm kiếm
- Trích xuất từ khóa chính xác (vị trí, địa điểm, ngành nghề)
- Tổng hợp kết quả một cách rõ ràng, dễ hiểu"""

# PhoGPT prompt template
TEMPLATE """### Câu hỏi: {{ .Prompt }}
### Trả lời:"""

MESSAGE system """{{ .System }}"""
MESSAGE user """### Câu hỏi: {{ .Content }}"""
MESSAGE assistant """### Trả lời: {{ .Content }}"""
EOF

    echo "✓ Modelfile created"
else
    echo "✓ Modelfile already exists"
fi

echo ""
echo "Step 4: Creating Ollama model..."
echo "-----------------------------------"
echo "Model name: ${MODEL_NAME}"
echo "This may take 1-2 minutes..."

ollama create "${MODEL_NAME}" -f "${MODELFILE}"

echo "✓ Model created successfully"

echo ""
echo "Step 5: Verifying model..."
echo "-----------------------------------"

if ollama list | grep -q "${MODEL_NAME}"; then
    echo "✓ Model verified in Ollama"
else
    echo "⚠ Warning: Model not found in Ollama list"
    echo "Run: ollama list"
fi

echo ""
echo "Step 6: Testing model..."
echo "-----------------------------------"
echo "Running test query..."
echo ""

ollama run "${MODEL_NAME}" "Xin chào, bạn có thể giúp tôi tìm việc làm không?"

echo ""
echo "=========================================="
echo "✓ Setup Complete!"
echo "=========================================="
echo ""
echo "Your PhoGPT model is ready: ${MODEL_NAME}"
echo ""
echo "Next steps:"
echo "1. Update your .env file:"
echo "   LLM_MODEL=${MODEL_NAME}"
echo "   QWEN_MODEL=${MODEL_NAME}"
echo ""
echo "2. Restart your job_bot service:"
echo "   python job_bot/main.py"
echo ""
echo "3. Test the integration:"
echo "   python job_bot/test_phogpt.py"
echo ""
echo "=========================================="
