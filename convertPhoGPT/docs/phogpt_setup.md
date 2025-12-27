# PhoGPT Setup Guide for Ollama

This guide shows how to integrate PhoGPT-4B-Chat with Ollama to replace Qwen while keeping the existing codebase architecture.

## Prerequisites

- Python 3.8+
- Ollama installed ([https://ollama.ai](https://ollama.ai))
- Git LFS for downloading large models
- At least 8GB RAM (16GB recommended)
- CUDA-compatible GPU (optional but recommended for better performance)

## Step 1: Convert PhoGPT to GGUF Format

Ollama uses GGUF (GPT-Generated Unified Format) for models. We need to convert PhoGPT from Hugging Face format to GGUF.

### Option A: Using llama.cpp converter (Recommended)

```bash
# Clone llama.cpp repository
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp

# Install Python dependencies
pip install -r requirements.txt

# Download PhoGPT model from Hugging Face
# You can use huggingface-cli or download manually
huggingface-cli download vinai/PhoGPT-4B-Chat --local-dir ./models/phogpt-4b-chat

# Convert to GGUF format
python convert.py ./models/phogpt-4b-chat --outfile ./models/phogpt-4b-chat.gguf --outtype f16

# Optional: Quantize to reduce size (q4_k_m is a good balance of quality/size)
./quantize ./models/phogpt-4b-chat.gguf ./models/phogpt-4b-chat-q4_k_m.gguf q4_k_m
```

### Option B: Use pre-converted GGUF (if available)

Check if someone has already converted PhoGPT to GGUF on Hugging Face:
```bash
# Search for GGUF versions
# Look for models tagged with "gguf" and "phogpt"
```

## Step 2: Create Ollama Modelfile

The Modelfile is saved at `job_bot/Modelfile.phogpt` (see next step).

## Step 3: Import Model to Ollama

```bash
# Navigate to job_bot directory
cd e:\QC_tech\SanViecLam\SanViecLam.Chatbot\job_bot

# Create the model in Ollama (use the path to your converted GGUF file)
ollama create phogpt-4b-chat -f Modelfile.phogpt

# Verify the model is available
ollama list

# Test the model
ollama run phogpt-4b-chat "Xin chào, bạn có thể giúp tôi tìm việc làm không?"
```

## Step 4: Update Environment Configuration

Update your `.env` file or environment variables:

```bash
# Change from Qwen to PhoGPT
LLM_MODEL=phogpt-4b-chat

# Keep other settings
OLLAMA_HOST=http://localhost:11434
LLM_NUM_PREDICT=4096
LLM_NUM_PREDICT_NORMALIZE=512
```

## Step 5: Test Integration

```bash
# Start your job_bot service
cd e:\QC_tech\SanViecLam\SanViecLam.Chatbot
python job_bot/main.py

# In another terminal, test the API
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "message": "Tìm việc kỹ sư phần mềm tại Hà Nội"}'
```

## Troubleshooting

### Model conversion fails
- Ensure you have enough disk space (PhoGPT-4B needs ~8GB)
- Check Python dependencies are correctly installed
- Try using the official llama.cpp Docker image

### Ollama can't load the model
- Verify GGUF file is not corrupted (check file size)
- Check Ollama version supports the GGUF format version
- Try running `ollama serve` with verbose logging

### Poor Vietnamese performance
- Adjust temperature in Modelfile (lower = more conservative)
- Increase `num_ctx` for longer context
- Try different quantization levels (q5_k_m or q6_k for better quality)

### Tool calling not working
- PhoGPT should work with Ollama's tool calling if using recent Ollama version
- Check that TOOLS definition in main.py is correct
- Verify response format matches expected structure

## Performance Optimization

### For CPU-only systems
```bash
# Use lighter quantization
./quantize ./models/phogpt-4b-chat.gguf ./models/phogpt-4b-chat-q4_0.gguf q4_0
```

### For GPU systems
```bash
# In Modelfile, uncomment or add:
# PARAMETER num_gpu 1
```

## Rollback to Qwen

If you need to switch back:
```bash
# Update .env
LLM_MODEL=qwen3:8b

# Restart service
```

## Additional Resources

- PhoGPT Repository: https://github.com/VinAIResearch/PhoGPT
- Ollama Documentation: https://github.com/ollama/ollama/blob/main/docs/modelfile.md
- llama.cpp Conversion: https://github.com/ggerganov/llama.cpp
- GGUF Format Spec: https://github.com/ggerganov/ggml/blob/master/docs/gguf.md

## Next Steps

1. Monitor performance with Vietnamese queries
2. Fine-tune temperature and context settings
3. Consider creating domain-specific system prompts
4. Benchmark response quality vs Qwen
