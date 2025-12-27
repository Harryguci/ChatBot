# Vietnamese LLM Models - GGUF Compatible

Based on research, here are the best Vietnamese-optimized models that **already support GGUF format** and work with Ollama.

## 🏆 Top Recommendations

### 1. Vistral-7B-Chat (BEST - Recommended)

**Model**: [Viet-Mistral/Vistral-7B-Chat](https://huggingface.co/Viet-Mistral/Vistral-7B-Chat)

**Performance**:
- ✅ **50.07% on VMLU benchmark** (beats ChatGPT's 46.33%)
- ✅ Based on Mistral 7B architecture (proven, reliable)
- ✅ Continual pre-training on Vietnamese texts
- ✅ Supervised fine-tuning with diverse Vietnamese instructions

**GGUF Availability**: Check for community GGUF conversions or convert yourself

**Why Choose This**:
- Best Vietnamese benchmark scores
- Modern architecture (Mistral-based)
- Active development
- Good balance of quality and size

### 2. Vietnamese Llama2 7B 40GB (BKAI-HUST)

**Model**: [TheBloke/vietnamese-llama2-7B-40GB-GGUF](https://huggingface.co/TheBloke/vietnamese-llama2-7B-40GB-GGUF)

**Performance**:
- ✅ Trained on 40GB Vietnamese corpus
- ✅ Strong Vietnamese understanding
- ✅ GGUF ready (multiple quantizations)

**GGUF Versions Available**:
- Q2_K (smallest, lowest quality)
- Q3_K_M
- Q4_K_M (recommended - good balance)
- Q5_K_M
- Q6_K
- Q8_0 (largest, best quality)

**Why Choose This**:
- Ready-to-use GGUF files
- Multiple quantization options
- Proven stable
- Good for production use

### 3. Llama-2-7B-Vietnamese-20k

**Model**: [TheBloke/Llama-2-7B-vietnamese-20k-GGUF](https://huggingface.co/TheBloke/Llama-2-7B-vietnamese-20k-GGUF)

**Performance**:
- ✅ Fine-tuned for Vietnamese instructions
- ⚠️ Smaller training dataset (20k samples)
- ✅ GGUF ready

**GGUF Versions Available**: Same as above (Q2_K to Q8_0)

**Why Choose This**:
- Ready-to-use
- Lighter training (faster but less comprehensive)

### 4. Qwen3 8B (Multilingual - Your Current Model)

**Model**: [Qwen/Qwen3-8B-GGUF](https://huggingface.co/Qwen/Qwen3-8B-GGUF)

**Performance**:
- ✅ Supports 29+ languages including Vietnamese
- ✅ Not Vietnamese-specific but very capable
- ✅ Already using this (qwen3:8b)

**Why Keep This**:
- Already working in your system
- Good general performance
- Proven reliable

## 📊 Comparison Table

| Model | Size | Vietnamese Focus | GGUF Ready | Benchmark | Recommendation |
|-------|------|------------------|------------|-----------|----------------|
| **Vistral-7B-Chat** | 7B | ⭐⭐⭐⭐⭐ | ✅ (community) | 50.07% VMLU | 🏆 Best Choice |
| **Vietnamese Llama2 40GB** | 7B | ⭐⭐⭐⭐ | ✅ (official) | Good | 🥈 Production Ready |
| **Llama2 Vietnamese 20k** | 7B | ⭐⭐⭐ | ✅ (official) | Okay | 🥉 Good Alternative |
| **Qwen3 8B** | 8B | ⭐⭐ | ✅ (official) | Very Good | Current |

## 🚀 Quick Start: Vietnamese Llama2 40GB (Easiest)

### Option 1: Direct Ollama (Recommended)

```bash
# Pull directly from Hugging Face
ollama run hf.co/TheBloke/vietnamese-llama2-7B-40GB-GGUF:Q4_K_M

# Or shorter
ollama pull hf.co/TheBloke/vietnamese-llama2-7B-40GB-GGUF
```

### Option 2: Download and Import

```bash
# 1. Download GGUF file
# Go to: https://huggingface.co/TheBloke/vietnamese-llama2-7B-40GB-GGUF
# Download: vietnamese-llama2-7b-40gb.Q4_K_M.gguf (~4.4GB)

# 2. Create Modelfile
cat > Modelfile.vietnamese <<EOF
FROM ./vietnamese-llama2-7b-40gb.Q4_K_M.gguf

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 50
PARAMETER num_ctx 4096
PARAMETER num_predict 2048

SYSTEM """Bạn là trợ lý AI chuyên nghiệp về tìm kiếm việc làm tại Việt Nam.
Trả lời bằng tiếng Việt, chính xác và thân thiện."""
EOF

# 3. Create Ollama model
ollama create vietnamese-llama2-7b -f Modelfile.vietnamese

# 4. Test
ollama run vietnamese-llama2-7b "Tìm việc kỹ sư phần mềm tại Hà Nội"
```

### Option 3: Use in Your Code (No Changes Needed!)

Update `.env`:
```env
# Just change the model name
LLM_MODEL=vietnamese-llama2-7b
QWEN_MODEL=vietnamese-llama2-7b
```

Restart your service - that's it!

## 🎯 Vistral-7B Setup (Best Quality)

Vistral doesn't have official GGUF yet, but you can:

### Check for Community GGUF

```bash
# Search Hugging Face
# https://huggingface.co/models?search=vistral+gguf
```

### Or Convert Yourself (If Needed)

Since Vistral is Mistral-based, it should convert properly:

```bash
# 1. Download Vistral
huggingface-cli download Viet-Mistral/Vistral-7B-Chat --local-dir ./vistral

# 2. Convert to GGUF
cd convertPhoGPT/phogpt_conversion/llama.cpp
python convert_hf_to_gguf.py ./vistral \
    --outfile ./vistral-7b-chat.gguf \
    --outtype f16

# 3. Quantize
./quantize ./vistral-7b-chat.gguf ./vistral-7b-chat-q4_k_m.gguf q4_k_m

# 4. Create Ollama model
ollama create vistral-7b -f Modelfile.vistral
```

## 📈 Performance Expectations

### Vietnamese Understanding

| Task | Qwen3 | Viet-Llama2 | Vistral |
|------|-------|-------------|---------|
| Vietnamese grammar | Good | Excellent | Excellent |
| Vietnamese idioms | Okay | Very Good | Excellent |
| Job search queries | Good | Very Good | Excellent |
| Tool calling | Excellent | Good | Very Good |
| General knowledge | Excellent | Good | Very Good |

### Resource Usage

| Model (Q4_K_M) | Size | RAM | VRAM (GPU) |
|----------------|------|-----|------------|
| Qwen3 8B | ~4.5GB | 6GB | 4GB |
| Viet-Llama2 7B | ~4.4GB | 6GB | 4GB |
| Vistral 7B | ~4.4GB | 6GB | 4GB |

## 🔧 Integration Steps

### Step 1: Choose Your Model

**For Production (Safest)**:
- ✅ Vietnamese Llama2 40GB (GGUF ready)

**For Best Quality**:
- ✅ Vistral-7B (may need conversion)

**Keep Current**:
- ✅ Qwen3 8B (already working)

### Step 2: Install/Download

```bash
# For Vietnamese Llama2 (easiest)
ollama pull hf.co/TheBloke/vietnamese-llama2-7B-40GB-GGUF:Q4_K_M

# Or download manually from:
# https://huggingface.co/TheBloke/vietnamese-llama2-7B-40GB-GGUF/tree/main
```

### Step 3: Create Ollama Model

```bash
# Create Modelfile
cat > job_bot/Modelfile.vietnamese <<EOF
FROM hf.co/TheBloke/vietnamese-llama2-7B-40GB-GGUF:Q4_K_M

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER num_ctx 4096
PARAMETER num_predict 2048

SYSTEM """Bạn là trợ lý AI chuyên nghiệp về tìm kiếm việc làm và tư vấn nghề nghiệp tại Việt Nam.

Nhiệm vụ của bạn:
1. Hiểu và phân tích yêu cầu tìm việc của người dùng
2. Sử dụng các công cụ (tools) để tìm kiếm việc làm phù hợp
3. Trả lời bằng tiếng Việt tự nhiên, chuyên nghiệp và thân thiện
4. Cung cấp thông tin chính xác, cụ thể về công việc"""
EOF

# Create model
cd job_bot
ollama create vietnamese-llama2-7b -f Modelfile.vietnamese
```

### Step 4: Update Configuration

```bash
# Edit .env or agent_lightning/.env
LLM_MODEL=vietnamese-llama2-7b
QWEN_MODEL=vietnamese-llama2-7b
```

### Step 5: Test

```bash
# Test Ollama model
ollama run vietnamese-llama2-7b "Xin chào, tìm việc kỹ sư phần mềm"

# Test your app
python job_bot/test_phogpt.py  # Use existing test script
```

## 🎁 Bonus: Automatic Fallback

You can configure multiple models:

```python
# In main.py
MODELS = [
    "vietnamese-llama2-7b",  # Primary
    "vistral-7b",             # Backup 1
    "qwen3:8b"                # Backup 2
]

for model in MODELS:
    try:
        client = ollama.Client()
        client.chat(model=model, messages=[{"role": "user", "content": "test"}])
        LLM_MODEL = model
        break
    except:
        continue
```

## 📚 Resources

- [Vistral-7B-Chat](https://huggingface.co/Viet-Mistral/Vistral-7B-Chat)
- [Vietnamese Llama2 7B 40GB GGUF](https://huggingface.co/TheBloke/vietnamese-llama2-7B-40GB-GGUF)
- [Llama-2-7B-vietnamese-20k GGUF](https://huggingface.co/TheBloke/Llama-2-7B-vietnamese-20k-GGUF)
- [Ollama GGUF Import Guide](https://huggingface.co/docs/hub/ollama)
- [VMLU Benchmark Results](https://huggingface.co/Viet-Mistral/Vistral-7B-Chat)

## ✅ Recommendation

**Start with Vietnamese Llama2 40GB** because:
- ✅ GGUF files ready to download
- ✅ No conversion needed
- ✅ Proven stable
- ✅ Good Vietnamese performance
- ✅ Easy to integrate (just change model name)

Then **upgrade to Vistral** once GGUF versions are available or after successful conversion.

## Sources

- [Vistral-7B-Chat on Hugging Face](https://huggingface.co/Viet-Mistral/Vistral-7B-Chat)
- [Vietnamese Llama2 7B 40GB GGUF](https://huggingface.co/TheBloke/vietnamese-llama2-7B-40GB-GGUF)
- [Llama-2-7B-vietnamese-20k GGUF](https://huggingface.co/TheBloke/Llama-2-7B-vietnamese-20k-GGUF)
- [Ollama GGUF Documentation](https://huggingface.co/docs/hub/ollama)
- [Best Ollama Models 2025](https://collabnix.com/best-ollama-models-in-2025-complete-performance-comparison/)
