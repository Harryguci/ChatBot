# PhoGPT Integration for SanViecLam Chatbot

⚠️ **UPDATE**: Official GGUF version available! No conversion needed!

## 🚀 Current Status

**✅ PRODUCTION READY**: PhoGPT successfully deployed in Docker Ollama

**Quick Start**:
```cmd
# Test integration
python test_phogpt_integration.py

# Check model
docker exec ollama ollama list | findstr phogpt
```

## ✅ Recommended: Use Official GGUF (EASIEST)

VinAI has released official PhoGPT GGUF files - **no conversion required**!

### For Ollama on Host Machine

**Windows:**
```cmd
cd e:\QC_tech\SanViecLam\SanViecLam.Chatbot\convertPhoGPT
setup_phogpt_official.bat
```

**Linux/Mac:**
```bash
cd /path/to/SanViecLam.Chatbot/convertPhoGPT
bash setup_phogpt_official.sh
```

### For Ollama in Docker 🐳 (DEPLOYED ✅)

**Production Setup**: Model already deployed and configured

**For New Deployments**:
```cmd
cd e:\QC_tech\SanViecLam\SanViecLam.Chatbot\convertPhoGPT

# Step 1: Download GGUF
powershell -ExecutionPolicy Bypass -File download_gguf.ps1

# Step 2: Setup in Docker
setup_phogpt_docker_manual.bat
```

**For Production Details**: See [docs/PRODUCTION_DEPLOYMENT.md](docs/PRODUCTION_DEPLOYMENT.md)

---

## 📚 Documentation

### Production Guides (Start Here)
- ⭐ [**PRODUCTION_DEPLOYMENT.md**](docs/PRODUCTION_DEPLOYMENT.md) - Complete deployment guide
- ⭐ [**QUICK_REFERENCE.md**](docs/QUICK_REFERENCE.md) - Commands cheat sheet
- ⭐ [**FILE_SUMMARY.md**](docs/FILE_SUMMARY.md) - File organization guide

### Detailed References
- [DOCKER_SETUP.md](docs/DOCKER_SETUP.md) - Docker-specific procedures
- [FINAL_SOLUTION.md](docs/FINAL_SOLUTION.md) - Development history
- [VIETNAMESE_MODELS_GGUF.md](docs/VIETNAMESE_MODELS_GGUF.md) - Alternative models

---

## ✅ What's Working

- ✅ Model deployed: `phogpt-4b-chat:latest` (2.36 GB)
- ✅ Docker integration complete
- ✅ Configuration updated: `agent_lightning/.env`
- ✅ Tests passed: Vietnamese responses working
- ✅ Production ready: All documentation complete

---

## ❌ Conversion Not Needed

~~The conversion scripts (`convert_phogpt.bat/sh`) are **not needed** because:~~
- ~~Manual conversion fails (tokenizer incompatibility)~~
- ✅ **Official GGUF files available** from VinAI

## What's in This Folder?

### Conversion Scripts
- **convert_phogpt.sh** / **.bat** - Downloads PhoGPT from Hugging Face and converts to GGUF format
- **setup_phogpt_ollama.sh** / **.bat** - Creates Ollama model from converted GGUF file

### Documentation
- **QUICKSTART.md** - 5-minute setup guide
- **SETUP_GUIDE.md** - Detailed setup instructions with troubleshooting
- **README_INTEGRATION.md** - Full integration documentation
- **IMPLEMENTATION_SUMMARY.md** - Technical implementation overview

### Generated Files (after conversion)
```
convertPhoGPT/
├── phogpt_conversion/         # Created during conversion
│   ├── llama.cpp/             # Cloned from GitHub
│   │   └── convert.py         # Conversion tool
│   └── models/
│       ├── phogpt-4b-chat-hf/ # Downloaded from Hugging Face
│       ├── phogpt-4b-chat.gguf           # FP16 version (~8GB)
│       └── phogpt-4b-chat-q4_k_m.gguf   # Quantized (~2.5GB) ✅ USE THIS
```

## Step-by-Step Process

### Step 1: Convert Model (10-20 minutes)
```bash
# Run the appropriate script for your OS
bash convert_phogpt.sh       # Linux/Mac
convert_phogpt.bat           # Windows
```

This will:
1. Clone llama.cpp repository
2. Download PhoGPT-4B-Chat from Hugging Face
3. Convert to GGUF format
4. Quantize to Q4_K_M (recommended)

### Step 2: Create Ollama Model (2-5 minutes)
```bash
# Option A: Use helper script (recommended)
bash setup_phogpt_ollama.sh  # Linux/Mac
setup_phogpt_ollama.bat      # Windows

# Option B: Manual setup
cd ../job_bot
# Update Modelfile.phogpt with GGUF path
ollama create phogpt-4b-chat -f Modelfile.phogpt
```

### Step 3: Configure Your Application
```bash
# Update environment file
# In agent_lightning/.env or job_bot/.env
LLM_MODEL=phogpt-4b-chat
QWEN_MODEL=phogpt-4b-chat
```

### Step 4: Test
```bash
# Test Ollama model directly
ollama run phogpt-4b-chat "Tìm việc kỹ sư phần mềm"

# Test with your application
cd ../job_bot
python test_phogpt.py
```

## File Structure Overview

```
SanViecLam.Chatbot/
├── convertPhoGPT/              ← YOU ARE HERE
│   ├── README.md               ← This file
│   ├── QUICKSTART.md           ← 5-min guide
│   ├── SETUP_GUIDE.md          ← Detailed guide
│   ├── README_INTEGRATION.md   ← Integration docs
│   ├── IMPLEMENTATION_SUMMARY.md
│   ├── convert_phogpt.sh       ← Conversion script (Linux/Mac)
│   ├── convert_phogpt.bat      ← Conversion script (Windows)
│   ├── setup_phogpt_ollama.sh  ← Ollama setup (Linux/Mac)
│   ├── setup_phogpt_ollama.bat ← Ollama setup (Windows)
│   └── phogpt_conversion/      ← Created after running scripts
│
├── job_bot/
│   ├── main.py                 ← Your chatbot (NO CHANGES NEEDED)
│   ├── Modelfile.phogpt        ← Ollama model config
│   ├── .env.phogpt             ← Environment template
│   └── test_phogpt.py          ← Test script
│
└── agent_lightning/
    └── .env                    ← Main config (update LLM_MODEL here)
```

## Prerequisites

- **Ollama** installed and running ([https://ollama.ai](https://ollama.ai))
- **Python 3.8+** with pip
- **Git** for cloning repositories
- **10GB free disk space** (temporary, final size ~2.5GB)
- **Internet connection** for downloading model

## Quick Links

- [5-Minute Quickstart](QUICKSTART.md) - Get started fast
- [Detailed Setup Guide](SETUP_GUIDE.md) - Step-by-step with screenshots
- [Integration Guide](README_INTEGRATION.md) - Full documentation
- [Implementation Details](IMPLEMENTATION_SUMMARY.md) - Technical overview

## Troubleshooting

### "ollama: command not found"
Install Ollama from https://ollama.ai

### "Error: no such file"
Update the `FROM` path in `../job_bot/Modelfile.phogpt` to point to your GGUF file

### Conversion fails
- Check disk space (need 10GB free)
- Verify Python and git are installed
- See [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed troubleshooting

### Model not calling tools
- Update Ollama to v0.1.20+
- Check TOOLS definition in main.py
- See integration guide

## Support

1. Check [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed instructions
2. Review [README_INTEGRATION.md](README_INTEGRATION.md) for integration help
3. See conversion script output for error messages

## License

PhoGPT is released under MIT License by VinAI Research.

## Resources

- **PhoGPT**: https://github.com/VinAIResearch/PhoGPT
- **PhoGPT Model**: https://huggingface.co/vinai/PhoGPT-4B-Chat
- **Ollama**: https://ollama.ai
- **llama.cpp**: https://github.com/ggerganov/llama.cpp
