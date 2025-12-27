#!/bin/bash
# Script to convert PhoGPT-4B-Chat to GGUF format for Ollama
# This version automatically creates and uses a virtual environment
# Usage: bash convert_phogpt.sh

set -e  # Exit on error

echo "=========================================="
echo "PhoGPT to GGUF Conversion Script"
echo "With Automatic Virtual Environment"
echo "=========================================="

# Configuration
PHOGPT_MODEL="vinai/PhoGPT-4B-Chat"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_DIR="${SCRIPT_DIR}/phogpt_conversion"
VENV_DIR="${WORK_DIR}/venv_conversion"
LLAMA_CPP_DIR="${WORK_DIR}/llama.cpp"
MODELS_DIR="${WORK_DIR}/models"
HF_MODEL_DIR="${MODELS_DIR}/phogpt-4b-chat-hf"
OUTPUT_GGUF="${MODELS_DIR}/phogpt-4b-chat.gguf"
QUANTIZED_GGUF="${MODELS_DIR}/phogpt-4b-chat-q4_k_m.gguf"

# Create working directory
mkdir -p "${WORK_DIR}"
mkdir -p "${MODELS_DIR}"

echo ""
echo "Step 1: Checking prerequisites..."
echo "-----------------------------------"

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    echo "Please install Python 3.8+ from https://www.python.org/"
    exit 1
fi

echo "✓ Python found"
PYTHON_VERSION=$(python3 --version 2>&1)
echo "  $PYTHON_VERSION"

# Check for git
if ! command -v git &> /dev/null; then
    echo "Error: git is not installed"
    echo "Please install git: sudo apt install git (Ubuntu/Debian) or brew install git (Mac)"
    exit 1
fi

echo "✓ git found"

echo ""
echo "Step 2: Setting up virtual environment..."
echo "-----------------------------------"

# Create virtual environment if it doesn't exist
if [ ! -d "${VENV_DIR}" ]; then
    echo "Creating new virtual environment at ${VENV_DIR}"
    python3 -m venv "${VENV_DIR}"
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "${VENV_DIR}/bin/activate"

if [ -z "$VIRTUAL_ENV" ]; then
    echo "Error: Failed to activate virtual environment"
    exit 1
fi

echo "✓ Virtual environment activated"
echo "  Python: $VIRTUAL_ENV"

# Upgrade pip in venv
echo "Upgrading pip in virtual environment..."
python -m pip install --upgrade pip --quiet

echo ""
echo "Step 3: Installing Python dependencies in venv..."
echo "-----------------------------------"

# Install huggingface-cli first
echo "Installing huggingface_hub..."
pip install "huggingface_hub[cli]" --quiet

# Install conversion dependencies
echo "Installing torch, transformers, sentencepiece, protobuf..."
pip install torch transformers sentencepiece protobuf --quiet

echo "✓ Dependencies installed in virtual environment"

echo ""
echo "Step 4: Cloning llama.cpp..."
echo "-----------------------------------"

if [ ! -d "${LLAMA_CPP_DIR}" ]; then
    git clone https://github.com/ggerganov/llama.cpp "${LLAMA_CPP_DIR}"
    cd "${LLAMA_CPP_DIR}"
else
    echo "llama.cpp already exists, pulling latest..."
    cd "${LLAMA_CPP_DIR}"
    git pull
fi

echo "✓ llama.cpp ready"

echo ""
echo "Step 5: Installing llama.cpp Python dependencies..."
echo "-----------------------------------"

if [ -f "requirements.txt" ]; then
    echo "Installing from llama.cpp requirements.txt..."
    pip install -r requirements.txt --quiet
fi

echo "✓ llama.cpp dependencies installed"

echo ""
echo "Step 6: Downloading PhoGPT from Hugging Face..."
echo "-----------------------------------"

cd "${WORK_DIR}"

if [ ! -d "${HF_MODEL_DIR}" ]; then
    echo "Downloading ${PHOGPT_MODEL}..."
    echo "This may take 10-20 minutes depending on your internet speed..."
    huggingface-cli download "${PHOGPT_MODEL}" --local-dir "${HF_MODEL_DIR}"
else
    echo "Model already downloaded at ${HF_MODEL_DIR}"
fi

echo "✓ PhoGPT downloaded"

echo ""
echo "Step 7: Converting to GGUF (FP16)..."
echo "-----------------------------------"

cd "${LLAMA_CPP_DIR}"

if [ ! -f "${OUTPUT_GGUF}" ]; then
    echo "Converting PhoGPT to GGUF format..."
    echo "This may take 5-10 minutes..."

    # Try new converter first (convert_hf_to_gguf.py)
    if [ -f "convert_hf_to_gguf.py" ]; then
        echo "Using convert_hf_to_gguf.py..."
        python convert_hf_to_gguf.py "${HF_MODEL_DIR}" \
            --outfile "${OUTPUT_GGUF}" \
            --outtype f16
    elif [ -f "convert.py" ]; then
        echo "Using convert.py..."
        python convert.py "${HF_MODEL_DIR}" \
            --outfile "${OUTPUT_GGUF}" \
            --outtype f16
    else
        echo "Error: No conversion script found (convert_hf_to_gguf.py or convert.py)"
        exit 1
    fi

    echo "✓ Converted to GGUF (FP16)"
else
    echo "GGUF file already exists: ${OUTPUT_GGUF}"
fi

echo ""
echo "Step 8: Building quantize tool..."
echo "-----------------------------------"

# Build quantize tool if not exists
if [ ! -f "./quantize" ]; then
    echo "Building quantize tool..."
    make quantize
    if [ $? -ne 0 ]; then
        echo "Warning: Failed to build quantize tool"
        echo "You can still use the FP16 GGUF file (larger but works)"
        echo "Or manually build quantize later"
    else
        echo "✓ quantize tool built"
    fi
else
    echo "✓ quantize tool already exists"
fi

echo ""
echo "Step 9: Quantizing to Q4_K_M (recommended)..."
echo "-----------------------------------"

if [ -f "./quantize" ]; then
    if [ ! -f "${QUANTIZED_GGUF}" ]; then
        echo "Quantizing model to reduce size..."
        echo "This may take 2-5 minutes..."
        ./quantize "${OUTPUT_GGUF}" "${QUANTIZED_GGUF}" q4_k_m
        echo "✓ Quantized to Q4_K_M"
    else
        echo "Quantized file already exists: ${QUANTIZED_GGUF}"
    fi
else
    echo "⚠ Skipping quantization (quantize tool not available)"
    echo "You can use the FP16 version: ${OUTPUT_GGUF}"
fi

echo ""
echo "Step 10: Model file information..."
echo "-----------------------------------"

echo "Original GGUF (FP16):"
if [ -f "${OUTPUT_GGUF}" ]; then
    ls -lh "${OUTPUT_GGUF}"
else
    echo "  Not found"
fi

if [ -f "${QUANTIZED_GGUF}" ]; then
    echo ""
    echo "Quantized GGUF (Q4_K_M):"
    ls -lh "${QUANTIZED_GGUF}"
fi

# Deactivate virtual environment
echo ""
echo "Deactivating virtual environment..."
deactivate 2>/dev/null || true

echo ""
echo "=========================================="
echo "✓ Conversion Complete!"
echo "=========================================="
echo ""
echo "Your converted model files are located at:"
echo "  FP16:    ${OUTPUT_GGUF}"
if [ -f "${QUANTIZED_GGUF}" ]; then
    echo "  Q4_K_M:  ${QUANTIZED_GGUF} (RECOMMENDED)"
fi
echo ""
echo "Virtual environment is at:"
echo "  ${VENV_DIR}"
echo "  (You can delete this folder after creating the Ollama model)"
echo ""
echo "=========================================="
echo "Next Steps:"
echo "=========================================="
echo ""
echo "1. Update ../job_bot/Modelfile.phogpt with the correct path:"
if [ -f "${QUANTIZED_GGUF}" ]; then
    echo "   FROM ${QUANTIZED_GGUF}"
else
    echo "   FROM ${OUTPUT_GGUF}"
fi
echo ""
echo "2. Create Ollama model:"
echo "   cd ../job_bot"
echo "   ollama create phogpt-4b-chat -f Modelfile.phogpt"
echo ""
echo "   OR use the quick setup script:"
echo "   cd ../convertPhoGPT"
echo "   bash setup_phogpt_ollama.sh"
echo ""
echo "3. Test the model:"
echo "   ollama run phogpt-4b-chat \"Xin chào, bạn có thể giúp tôi tìm việc làm không?\""
echo ""
echo "4. Update your .env file:"
echo "   LLM_MODEL=phogpt-4b-chat"
echo ""
echo "=========================================="
