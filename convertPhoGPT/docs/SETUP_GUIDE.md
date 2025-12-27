# PhoGPT Setup Guide for Docker Ollama

## Current Status

Your Ollama is running in Docker:
- **Container**: `ollama` (ID: e4016d810829)
- **Port**: 11434 (mapped to host)
- **Image**: ollama/ollama

## Setup Process

### Step 1: Download GGUF File ✅ (In Progress)

The PowerShell script `download_gguf.ps1` is currently downloading the 2.36 GB file.

**Current download:**
```powershell
cd e:\QC_tech\SanViecLam\SanViecLam.Chatbot\convertPhoGPT
powershell -ExecutionPolicy Bypass -File download_gguf.ps1
```

This will download to: `convertPhoGPT\models\phogpt-4b-chat-q4_k_m.gguf`

### Step 2: Setup Model in Docker (After Download)

Once the download completes, run:

```cmd
cd e:\QC_tech\SanViecLam\SanViecLam.Chatbot\convertPhoGPT
setup_phogpt_docker_manual.bat
```

This script will:
1. ✅ Check Docker is running
2. ✅ Check Ollama container is running
3. ✅ Verify GGUF file exists
4. ✅ Copy GGUF to Docker container (/tmp/)
5. ✅ Create Modelfile inside container
6. ✅ Run `ollama create phogpt-4b-chat`
7. ✅ Test the model
8. ✅ Cleanup temp files

### Step 3: Update Configuration

Edit your `.env` file:

```env
# Change from:
LLM_MODEL=qwen3:8b
QWEN_MODEL=qwen3:8b

# To:
LLM_MODEL=phogpt-4b-chat
QWEN_MODEL=phogpt-4b-chat

# Ollama host (should already be correct):
OLLAMA_HOST=http://localhost:11434
```

### Step 4: Restart Application

```cmd
python job_bot\main.py
```

### Step 5: Test Integration

**Test via Ollama CLI (in Docker):**
```cmd
docker exec -i ollama ollama run phogpt-4b-chat "Tìm việc kỹ sư phần mềm tại Hà Nội"
```

**Test via API:**
```cmd
curl -X POST http://localhost:11434/api/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"model\":\"phogpt-4b-chat\",\"messages\":[{\"role\":\"user\",\"content\":\"Xin chào\"}],\"stream\":false}"
```

**Test via Python:**
```python
python job_bot/test_phogpt.py
```

## File Overview

### Created Files

| File | Purpose | Status |
|------|---------|--------|
| `download_gguf.ps1` | Download GGUF from Hugging Face | ✅ Running |
| `setup_phogpt_docker_manual.bat` | Docker setup (after download) | ✅ Ready |
| `SETUP_GUIDE.md` | This file | ✅ Complete |
| `models/phogpt-4b-chat-q4_k_m.gguf` | Model file | ⏳ Downloading |

### Alternative Files (Not Needed)

- `setup_phogpt_docker.bat` - Has huggingface-cli PATH issue
- `download_phogpt.bat` - Had wrong filename (lowercase)
- `convert_phogpt.bat` - Conversion not needed (official GGUF exists)

## Troubleshooting

### Download Issues

**Check download progress:**
```cmd
cd convertPhoGPT\models
dir phogpt-4b-chat-q4_k_m.gguf
```

Expected size: ~2.36 GB (2,536,000,000 bytes)

**If download fails:**
1. Manual download from browser:
   - https://huggingface.co/vinai/PhoGPT-4B-Chat-gguf/tree/main
   - Click on `PhoGPT-4B-Chat-Q4_K_M.gguf`
   - Click download button
   - Save to: `convertPhoGPT\models\phogpt-4b-chat-q4_k_m.gguf` (rename to lowercase)

2. Or retry PowerShell script:
   ```cmd
   powershell -ExecutionPolicy Bypass -File download_gguf.ps1
   ```

### Docker Issues

**Container not running:**
```cmd
docker start ollama
```

**Port not accessible:**
```cmd
docker ps
# Check that 11434->11434 mapping exists
```

**Model not created:**
```cmd
docker exec ollama ollama list
# Should show phogpt-4b-chat

# If missing, re-run setup:
setup_phogpt_docker_manual.bat
```

### Application Issues

**Model not found error:**
```
Error: model "phogpt-4b-chat" not found
```

Solution: Verify model exists in Docker:
```cmd
docker exec ollama ollama list
```

**Connection refused:**
```
Error: connection refused localhost:11434
```

Solution: Check Ollama container is running:
```cmd
docker ps | findstr ollama
```

**Vietnamese responses poor quality:**

This might happen if:
1. PhoGPT not good at tool calling → Consider hybrid approach
2. Temperature too high → Adjust in Modelfile
3. Context window too small → Increase num_ctx

## Performance Comparison

### Model Sizes
- Qwen 3 8B: ~4.5 GB
- PhoGPT 4B Q4_K_M: ~2.36 GB (47% smaller!)
- PhoGPT 4B Q8_0: ~3.92 GB (higher quality)

### Vietnamese Quality
- **PhoGPT**: Excellent (102B Vietnamese tokens training)
- **Qwen**: Good (multilingual, decent Vietnamese)

### Tool Calling
- **Qwen**: Excellent (specifically trained)
- **PhoGPT**: Unknown (needs testing)

## Rollback Plan

If PhoGPT doesn't work well:

**1. Quick rollback (keep both models):**
```env
# In .env
LLM_MODEL=qwen3:8b
QWEN_MODEL=qwen3:8b
```

**2. Full removal:**
```cmd
docker exec ollama ollama rm phogpt-4b-chat
```

## Next Steps After Setup

1. **Test basic Vietnamese understanding**
   ```
   Query: "Tìm việc công nhân may ở Cao Bằng"
   Expected: Should understand Vietnamese job terms
   ```

2. **Test tool calling**
   ```
   Query: "Có việc làm kỹ sư phần mềm không?"
   Expected: Should call job_search tool
   ```

3. **Compare with Qwen**
   - Run same queries with both models
   - Check response quality
   - Check tool calling accuracy

4. **Monitor performance**
   - Response time
   - Memory usage
   - Docker container stats: `docker stats ollama`

## Summary

| Step | Command | Status |
|------|---------|--------|
| 1. Download | `download_gguf.ps1` | ⏳ In progress |
| 2. Setup Docker | `setup_phogpt_docker_manual.bat` | ⏭️ Next |
| 3. Update config | Edit `.env` | ⏭️ After setup |
| 4. Test | Various commands | ⏭️ After config |
| 5. Production | Deploy if good | ⏭️ After testing |

---

**Current Status**: Waiting for 2.36 GB download to complete (~10-20 minutes)

**Next Action**: Run `setup_phogpt_docker_manual.bat` after download completes
