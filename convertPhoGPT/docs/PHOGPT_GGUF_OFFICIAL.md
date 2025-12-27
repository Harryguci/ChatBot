# ✅ Official PhoGPT GGUF - No Conversion Needed!

Great news! VinAI has released **official GGUF versions** of PhoGPT that work directly with Ollama.

## 📦 Available Models

**Model**: [vinai/PhoGPT-4B-Chat-gguf](https://huggingface.co/vinai/PhoGPT-4B-Chat-gguf)

| Quantization | Size | Quality | Use Case |
|--------------|------|---------|----------|
| **Q4_K_M** | 2.36 GB | Good | ✅ Recommended - Best balance |
| **Q8_0** | 3.92 GB | Excellent | High quality, more memory |

**Specifications**:
- 🇻🇳 Vietnamese-optimized
- 📊 Trained on 102B Vietnamese tokens
- 💬 Fine-tuned on 70K instructions + 290K conversations
- 📝 8192 token context length
- 🎯 20,480 vocabulary size

## 🚀 Quick Setup (5 Minutes)

### Option 1: Direct Pull from Hugging Face (Easiest)

```bash
# Pull Q4_K_M (recommended)
ollama pull hf.co/vinai/PhoGPT-4B-Chat-gguf:Q4_K_M

# Or Q8_0 (higher quality)
ollama pull hf.co/vinai/PhoGPT-4B-Chat-gguf:Q8_0
```

### Option 2: Download and Import

#### Step 1: Download GGUF File

```bash
# Method A: Using huggingface-cli
huggingface-cli download vinai/PhoGPT-4B-Chat-gguf \
    phogpt-4b-chat-q4_k_m.gguf \
    --local-dir ./models

# Method B: Manual download
# Go to: https://huggingface.co/vinai/PhoGPT-4B-Chat-gguf/tree/main
# Download: phogpt-4b-chat-q4_k_m.gguf (2.36 GB)
```

#### Step 2: Create Modelfile

```bash
cd e:\QC_tech\SanViecLam\SanViecLam.Chatbot\job_bot

# Create Modelfile
cat > Modelfile.phogpt <<EOF
# Official PhoGPT 4B Chat GGUF
FROM ./models/phogpt-4b-chat-q4_k_m.gguf

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
```

#### Step 3: Create Ollama Model

```bash
ollama create phogpt-4b-chat -f Modelfile.phogpt
```

#### Step 4: Test

```bash
ollama run phogpt-4b-chat "Xin chào, tìm việc kỹ sư phần mềm tại Hà Nội"
```

#### Step 5: Update Your Application

```bash
# Edit .env or agent_lightning/.env
LLM_MODEL=phogpt-4b-chat
QWEN_MODEL=phogpt-4b-chat

# Restart service
python job_bot/main.py
```

## 🎯 Complete Setup Script

Save this as `setup_phogpt_official.bat` (Windows):

```batch
@echo off
echo ==========================================
echo PhoGPT Official GGUF Setup
echo ==========================================

echo.
echo Step 1: Downloading PhoGPT GGUF...
huggingface-cli download vinai/PhoGPT-4B-Chat-gguf phogpt-4b-chat-q4_k_m.gguf --local-dir ./models

echo.
echo Step 2: Creating Ollama model...
cd job_bot
ollama create phogpt-4b-chat -f Modelfile.phogpt

echo.
echo Step 3: Testing model...
ollama run phogpt-4b-chat "Xin chào, bạn là ai?"

echo.
echo ==========================================
echo Setup Complete!
echo ==========================================
echo.
echo Update your .env file:
echo   LLM_MODEL=phogpt-4b-chat
echo.
echo Then restart your service:
echo   python job_bot/main.py
echo.
pause
```

Or Linux/Mac (`setup_phogpt_official.sh`):

```bash
#!/bin/bash
echo "=========================================="
echo "PhoGPT Official GGUF Setup"
echo "=========================================="

echo ""
echo "Step 1: Downloading PhoGPT GGUF..."
huggingface-cli download vinai/PhoGPT-4B-Chat-gguf \
    phogpt-4b-chat-q4_k_m.gguf \
    --local-dir ./models

echo ""
echo "Step 2: Creating Ollama model..."
cd job_bot
ollama create phogpt-4b-chat -f Modelfile.phogpt

echo ""
echo "Step 3: Testing model..."
ollama run phogpt-4b-chat "Xin chào, bạn là ai?"

echo ""
echo "=========================================="
echo "✓ Setup Complete!"
echo "=========================================="
echo ""
echo "Update your .env file:"
echo "  LLM_MODEL=phogpt-4b-chat"
echo ""
echo "Then restart your service:"
echo "  python job_bot/main.py"
```

## 📊 Comparison

| Feature | Official PhoGPT GGUF | Converted PhoGPT | Qwen3 8B |
|---------|----------------------|------------------|----------|
| **Setup Difficulty** | ⭐ Very Easy | ❌ Failed | ⭐ Easy |
| **Download Size** | 2.36 GB | N/A | ~4.5 GB |
| **Vietnamese Quality** | ⭐⭐⭐⭐⭐ | N/A | ⭐⭐⭐ |
| **Tool Calling** | ⭐⭐⭐ | N/A | ⭐⭐⭐⭐⭐ |
| **Speed (GPU)** | Fast | N/A | Fast |
| **Official Support** | ✅ Yes | ❌ No | ✅ Yes |

## 🎁 Why This is Better

**vs Manual Conversion**:
- ✅ No conversion errors
- ✅ Official VinAI release
- ✅ Pre-optimized quantization
- ✅ 5-minute setup vs hours of troubleshooting

**vs Other Vietnamese Models**:
- ✅ Most Vietnamese-focused (102B tokens)
- ✅ Largest instruction dataset (70K + 290K)
- ✅ Official from VinAI Research
- ✅ Active maintenance

## 🔧 Troubleshooting

### Download Fails

```bash
# Try alternative download
wget https://huggingface.co/vinai/PhoGPT-4B-Chat-gguf/resolve/main/phogpt-4b-chat-q4_k_m.gguf

# Or use browser
# Go to: https://huggingface.co/vinai/PhoGPT-4B-Chat-gguf/tree/main
# Click download
```

### Model Not Found in Ollama

```bash
# List models
ollama list

# If missing, recreate
ollama create phogpt-4b-chat -f Modelfile.phogpt
```

### Poor Tool Calling

PhoGPT may not be as good at tool calling as Qwen. Consider:
- Using more explicit system prompts
- Adding examples in the system message
- Hybrid approach (Qwen for tools, PhoGPT for responses)

## 📚 Resources

- **Model Card**: https://huggingface.co/vinai/PhoGPT-4B-Chat-gguf
- **Original PhoGPT**: https://github.com/VinAIResearch/PhoGPT
- **Technical Paper**: [arXiv:2311.02945](https://arxiv.org/abs/2311.02945)
- **License**: BSD-3-Clause

## 📝 Citation

If you use PhoGPT in your work:

```bibtex
@article{PhoGPT,
  title     = {{PhoGPT: Generative Pre-training for Vietnamese}},
  author    = {Dat Quoc Nguyen and Linh The Nguyen and Chi Tran and
               Dung Ngoc Nguyen and Dinh Phung and Hung Bui},
  journal   = {arXiv preprint},
  volume    = {arXiv:2311.02945},
  year      = {2023}
}
```

## ✅ Next Steps

1. **Download**: Get `phogpt-4b-chat-q4_k_m.gguf` (2.36 GB)
2. **Create**: Make Ollama model with Modelfile
3. **Test**: Try `ollama run phogpt-4b-chat`
4. **Deploy**: Update `.env` and restart service
5. **Monitor**: Compare Vietnamese quality vs Qwen

## 🎯 Recommendation

**Use this official GGUF version** instead of:
- ❌ Manual conversion (failed)
- ❌ Direct transformers integration (complex)
- ✅ Simple, official, works out of the box

This is the **easiest and best solution** for Vietnamese support!
