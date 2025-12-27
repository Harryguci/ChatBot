# PhoGPT Quick Start - 5 Minutes Setup

Replace Qwen with PhoGPT (Vietnamese-optimized) in 5 steps.

## Prerequisites

- Ollama installed and running
- Python 3.8+
- 10GB free disk space

## Step-by-Step

### 1️⃣ Convert PhoGPT to GGUF

**Windows:**
```cmd
cd e:\QC_tech\SanViecLam\SanViecLam.Chatbot\convertPhoGPT
convert_phogpt.bat
```

**Linux/Mac:**
```bash
cd /path/to/SanViecLam.Chatbot/convertPhoGPT
bash convert_phogpt.sh
```

⏱️ This takes 10-20 minutes depending on internet speed.

### 2️⃣ Create Ollama Model

**Option A: Automatic (Recommended)**
```bash
# Windows
setup_phogpt_ollama.bat

# Linux/Mac
bash setup_phogpt_ollama.sh
```

**Option B: Manual**
```bash
cd ../job_bot
# Update Modelfile.phogpt FROM path to:
# FROM ../convertPhoGPT/phogpt_conversion/models/phogpt-4b-chat-q4_k_m.gguf

ollama create phogpt-4b-chat -f Modelfile.phogpt
```

Expected output:
```
transferring model data
using existing layer sha256:...
creating new layer sha256:...
writing manifest
success
```

### 3️⃣ Test the Model

```bash
ollama run phogpt-4b-chat "Xin chào, tìm việc kỹ sư phần mềm ở Hà Nội"
```

If you see a Vietnamese response, it's working! Press `Ctrl+D` to exit.

### 4️⃣ Update Configuration

**Option A: Update main .env file**

Edit `agent_lightning/.env`:
```env
LLM_MODEL=phogpt-4b-chat
QWEN_MODEL=phogpt-4b-chat
```

**Option B: Create job_bot specific .env**

Copy the example:
```bash
cp job_bot/.env.phogpt job_bot/.env
```

### 5️⃣ Restart Service

```bash
# Stop your current service (Ctrl+C)

# Start with new model
python job_bot/main.py
```

Check startup logs for:
```
[LLM] Model: phogpt-4b-chat, Max tokens: 4096, ...
```

## Verification

### Test 1: Health Check
```bash
curl http://localhost:8000/health
```

Expected: `{"status":"ok","model":"phogpt-4b-chat"}`

### Test 2: Chat Request
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","message":"Tìm việc công nhân may ở Cao Bằng"}'
```

Should return job search results in Vietnamese.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ollama: command not found` | Install Ollama: https://ollama.ai |
| `Error: no such file` | Check path in ../job_bot/Modelfile.phogpt |
| `Model not found` | Run step 2 again |
| Service won't start | Check logs, verify .env changes |

## Rollback

To switch back to Qwen:

1. Update `.env`: `LLM_MODEL=qwen3:8b`
2. Restart service

## What's Next?

- 📊 Monitor Vietnamese query quality
- ⚙️ Tune parameters in ../job_bot/Modelfile.phogpt
- 🎯 Compare with Qwen performance
- 📝 Collect user feedback

## Need Help?

See detailed guides:
- [README.md](README.md) - This folder overview
- [SETUP_GUIDE.md](SETUP_GUIDE.md) - Detailed setup guide
- [README_INTEGRATION.md](README_INTEGRATION.md) - Full integration docs
