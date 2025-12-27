#!/bin/bash
# Setup Official PhoGPT GGUF for Ollama (Docker Version)
# For Ollama running in Docker container

set -e

echo "=========================================="
echo "PhoGPT Official GGUF Setup (Docker)"
echo "=========================================="
echo ""
echo "This script will:"
echo "1. Download official PhoGPT GGUF (2.36 GB)"
echo "2. Copy to Docker container"
echo "3. Create Ollama model in Docker"
echo "4. Test the model"
echo ""

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELS_DIR="${SCRIPT_DIR}/models"
GGUF_FILE="phogpt-4b-chat-q4_k_m.gguf"
MODEL_NAME="phogpt-4b-chat"
CONTAINER_NAME="ollama"

# Check if Docker is running
echo "Step 0: Checking Docker..."
echo "-----------------------------------"

if ! docker ps &> /dev/null; then
    echo "Error: Docker is not running"
    echo "Please start Docker"
    exit 1
fi

echo "✓ Docker is running"

# Check if Ollama container exists
if ! docker ps | grep -q "${CONTAINER_NAME}"; then
    echo "Error: Ollama container not found"
    echo "Please start Ollama container:"
    echo "  docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama"
    exit 1
fi

echo "✓ Ollama container is running"

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
echo "Step 3: Copying GGUF to Docker container..."
echo "-----------------------------------"

# Copy GGUF file to Docker container's temp directory
docker cp "${GGUF_FILE}" "${CONTAINER_NAME}:/tmp/${GGUF_FILE}"

echo "✓ File copied to container"

echo ""
echo "Step 4: Creating Modelfile in container..."
echo "-----------------------------------"

# Create Modelfile inside container
docker exec -i "${CONTAINER_NAME}" sh -c 'cat > /tmp/Modelfile.phogpt' <<'EOF'
FROM /tmp/phogpt-4b-chat-q4_k_m.gguf

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 50
PARAMETER num_ctx 4096
PARAMETER num_predict 2048
PARAMETER stop "### Câu hỏi:"
PARAMETER stop "<|endoftext|>"

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

TEMPLATE """### Câu hỏi: {{ .Prompt }}
### Trả lời:"""

MESSAGE system """{{ .System }}"""
MESSAGE user """### Câu hỏi: {{ .Content }}"""
MESSAGE assistant """### Trả lời: {{ .Content }}"""
EOF

echo "✓ Modelfile created in container"

echo ""
echo "Step 5: Creating Ollama model in Docker..."
echo "-----------------------------------"
echo "Model name: ${MODEL_NAME}"
echo "This may take 1-2 minutes..."

# Create model inside container
docker exec "${CONTAINER_NAME}" ollama create "${MODEL_NAME}" -f /tmp/Modelfile.phogpt

echo "✓ Model created successfully"

echo ""
echo "Step 6: Verifying model..."
echo "-----------------------------------"

if docker exec "${CONTAINER_NAME}" ollama list | grep -q "${MODEL_NAME}"; then
    echo "✓ Model verified in Ollama"
else
    echo "⚠ Warning: Model not found in Ollama list"
fi

echo ""
echo "Step 7: Testing model..."
echo "-----------------------------------"
echo "Running test query..."
echo ""

docker exec -i "${CONTAINER_NAME}" ollama run "${MODEL_NAME}" "Xin chào, bạn có thể giúp tôi tìm việc làm không?"

echo ""
echo "Step 8: Cleanup temp files in container..."
echo "-----------------------------------"

docker exec "${CONTAINER_NAME}" sh -c "rm -f /tmp/${GGUF_FILE} /tmp/Modelfile.phogpt"
echo "✓ Cleanup complete"

echo ""
echo "=========================================="
echo "✓ Setup Complete!"
echo "=========================================="
echo ""
echo "Your PhoGPT model is ready: ${MODEL_NAME}"
echo "Running in Docker container: ${CONTAINER_NAME}"
echo ""
echo "Docker Info:"
docker exec "${CONTAINER_NAME}" ollama list | grep "${MODEL_NAME}"
echo ""
echo "Next steps:"
echo "1. Update your .env file:"
echo "   LLM_MODEL=${MODEL_NAME}"
echo "   QWEN_MODEL=${MODEL_NAME}"
echo "   OLLAMA_HOST=http://localhost:11434"
echo ""
echo "2. Restart your job_bot service:"
echo "   python job_bot/main.py"
echo ""
echo "3. Test the integration:"
echo "   curl -X POST http://localhost:11434/api/chat \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"model\":\"${MODEL_NAME}\",\"messages\":[{\"role\":\"user\",\"content\":\"Xin chào\"}]}'"
echo ""
echo "=========================================="
