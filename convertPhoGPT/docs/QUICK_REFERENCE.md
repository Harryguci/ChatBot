# PhoGPT Quick Reference Guide

**Model**: phogpt-4b-chat | **Size**: 2.36 GB | **Status**: ✅ Production Ready

---

## Quick Commands

### Verify Model
```cmd
docker exec ollama ollama list | findstr phogpt
```
Expected: `phogpt-4b-chat:latest    bb63fc4b2d64    2.4 GB`

### Test Model
```cmd
docker exec ollama ollama run phogpt-4b-chat "Xin chào"
```

### Test API
```cmd
curl -X POST http://localhost:11434/api/chat -d "{\"model\":\"phogpt-4b-chat\",\"messages\":[{\"role\":\"user\",\"content\":\"Tìm việc kỹ sư\"}],\"stream\":false}"
```

### Check Docker Status
```cmd
docker ps | findstr ollama
docker stats ollama --no-stream
```

### View Logs
```cmd
docker logs ollama --tail 50
```

---

## Configuration

### Current Setup (Production)
**File**: `agent_lightning/.env`
```env
LLM_MODEL=phogpt-4b-chat
QWEN_MODEL=phogpt-4b-chat
INTENT_MODEL=phogpt-4b-chat
OLLAMA_HOST=http://localhost:11434
```

### Rollback to Qwen
```env
LLM_MODEL=qwen3:8b-q4_K_M
QWEN_MODEL=qwen3:8b-q4_K_M
INTENT_MODEL=qwen2.5:3b
```

---

## Troubleshooting

### Model Not Found
```cmd
# List all models
docker exec ollama ollama list

# Recreate model
cd convertPhoGPT
setup_phogpt_docker_manual.bat
```

### Container Not Running
```cmd
docker start ollama
# Or check status
docker ps -a | findstr ollama
```

### Slow Responses
```cmd
# Check resources
docker stats ollama

# Check model size
docker exec ollama ollama list
```

### API Connection Error
```cmd
# Test connectivity
curl http://localhost:11434/api/tags

# Check port mapping
docker port ollama
```

---

## File Locations

### Model File
```
convertPhoGPT/models/phogpt-4b-chat-q4_k_m.gguf (2.36 GB)
```

### Configuration
```
agent_lightning/.env
```

### Setup Scripts
```
convertPhoGPT/setup_phogpt_docker_manual.bat  # Main setup
convertPhoGPT/download_gguf.ps1               # Download
```

### Tests
```
test_phogpt_integration.py                    # Integration test
```

### Documentation
```
convertPhoGPT/docs/PRODUCTION_DEPLOYMENT.md   # Full guide
convertPhoGPT/docs/DOCKER_SETUP.md            # Docker details
convertPhoGPT/README.md                       # Overview
```

---

## Common Tasks

### Deploy to New Server
```cmd
# 1. Download model
cd convertPhoGPT
powershell -ExecutionPolicy Bypass -File download_gguf.ps1

# 2. Setup in Docker
setup_phogpt_docker_manual.bat

# 3. Update config (edit agent_lightning/.env)
LLM_MODEL=phogpt-4b-chat

# 4. Test
python test_phogpt_integration.py

# 5. Restart application
python job_bot/main.py
```

### Update Model
```cmd
# 1. Remove old model
docker exec ollama ollama rm phogpt-4b-chat

# 2. Download new version
powershell -ExecutionPolicy Bypass -File download_gguf.ps1

# 3. Re-run setup
setup_phogpt_docker_manual.bat
```

### Performance Check
```cmd
# 1. Test response time
python test_phogpt_integration.py

# 2. Check Docker resources
docker stats ollama --no-stream

# 3. View recent queries (in app logs)
tail -f logs/job_bot.log
```

---

## Model Information

### PhoGPT Specifications
- **Name**: phogpt-4b-chat
- **Parameters**: 4 billion
- **Quantization**: Q4_K_M (4-bit)
- **Size**: 2.36 GB
- **Context Window**: 4096 tokens
- **Max Output**: 2048 tokens
- **Training**: 102B Vietnamese tokens
- **Source**: VinAI Research

### Docker Container
- **Name**: ollama
- **Port**: 11434 (host) → 11434 (container)
- **Volume**: ollama:/root/.ollama
- **Image**: ollama/ollama:latest

---

## API Examples

### Basic Chat
```python
import requests

response = requests.post("http://localhost:11434/api/chat", json={
    "model": "phogpt-4b-chat",
    "messages": [
        {"role": "user", "content": "Tìm việc kỹ sư phần mềm"}
    ],
    "stream": False
})

print(response.json()["message"]["content"])
```

### With System Prompt
```python
response = requests.post("http://localhost:11434/api/chat", json={
    "model": "phogpt-4b-chat",
    "messages": [
        {"role": "system", "content": "Bạn là trợ lý tìm việc làm."},
        {"role": "user", "content": "Tìm việc tại Hà Nội"}
    ],
    "options": {
        "temperature": 0.7,
        "num_predict": 512
    },
    "stream": False
})
```

### Streaming Response
```python
response = requests.post("http://localhost:11434/api/chat", json={
    "model": "phogpt-4b-chat",
    "messages": [{"role": "user", "content": "Xin chào"}],
    "stream": True
}, stream=True)

for line in response.iter_lines():
    if line:
        print(json.loads(line)["message"]["content"], end="")
```

---

## Monitoring

### Key Metrics
1. **Response Time**: Should be 0.5-4s
2. **Error Rate**: Should be <1%
3. **Memory Usage**: ~3-4 GB in Docker
4. **GPU Usage**: 40-60% (if applicable)

### Health Check
```cmd
# Quick test
curl http://localhost:11434/api/tags

# Full test
python test_phogpt_integration.py
```

---

## Emergency Contacts

### Quick Rollback
1. Edit `agent_lightning/.env` → Change to `qwen3:8b-q4_K_M`
2. Restart application
3. No need to change Docker

### Remove Model
```cmd
docker exec ollama ollama rm phogpt-4b-chat
```

### Restart Docker
```cmd
docker restart ollama
# Wait 10 seconds
docker exec ollama ollama list
```

---

## Resources

- **PhoGPT GitHub**: https://github.com/VinAIResearch/PhoGPT
- **GGUF Model**: https://huggingface.co/vinai/PhoGPT-4B-Chat-gguf
- **Ollama Docs**: https://ollama.com/docs
- **Full Guide**: [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md)

---

**Last Updated**: 2025-12-17
