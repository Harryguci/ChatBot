# PhoGPT Setup for Ollama in Docker

Since your Ollama is running in Docker, the setup process is slightly different.

## Current Docker Setup

```bash
CONTAINER ID   IMAGE           COMMAND               PORTS                     NAMES
e4016d810829   ollama/ollama   "/bin/ollama serve"   0.0.0.0:11434->11434/tcp  ollama
```

## 🚀 Quick Setup (Docker Version)

### Windows

```cmd
cd e:\QC_tech\SanViecLam\SanViecLam.Chatbot\convertPhoGPT
setup_phogpt_docker.bat
```

### Linux/Mac

```bash
cd /path/to/SanViecLam.Chatbot/convertPhoGPT
bash setup_phogpt_docker.sh
```

## What the Script Does

1. ✅ Downloads GGUF file to local machine (2.36 GB)
2. ✅ Copies GGUF to Docker container
3. ✅ Creates Modelfile inside container
4. ✅ Runs `ollama create` inside container
5. ✅ Cleans up temp files
6. ✅ Tests the model

## Manual Setup (If Preferred)

### Step 1: Download GGUF

```bash
# On host machine
cd convertPhoGPT/models
huggingface-cli download vinai/PhoGPT-4B-Chat-gguf phogpt-4b-chat-q4_k_m.gguf --local-dir .
```

### Step 2: Copy to Docker Container

```bash
# Copy GGUF to container
docker cp models/phogpt-4b-chat-q4_k_m.gguf ollama:/tmp/

# Verify
docker exec ollama ls -lh /tmp/phogpt-4b-chat-q4_k_m.gguf
```

### Step 3: Create Modelfile in Container

```bash
# Create Modelfile inside container
docker exec -i ollama sh -c 'cat > /tmp/Modelfile.phogpt' <<'EOF'
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
4. Cung cấp thông tin chính xác, cụ thể về công việc"""

TEMPLATE """### Câu hỏi: {{ .Prompt }}
### Trả lời:"""

MESSAGE system """{{ .System }}"""
MESSAGE user """### Câu hỏi: {{ .Content }}"""
MESSAGE assistant """### Trả lời: {{ .Content }}"""
EOF
```

### Step 4: Create Model in Container

```bash
# Create model
docker exec ollama ollama create phogpt-4b-chat -f /tmp/Modelfile.phogpt

# Verify
docker exec ollama ollama list
```

### Step 5: Test

```bash
# Test inside container
docker exec -i ollama ollama run phogpt-4b-chat "Xin chào, tìm việc kỹ sư"

# Test via API (from host)
curl -X POST http://localhost:11434/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "phogpt-4b-chat",
    "messages": [{"role": "user", "content": "Xin chào"}],
    "stream": false
  }'
```

### Step 6: Cleanup (Optional)

```bash
# Remove temp files from container
docker exec ollama rm /tmp/phogpt-4b-chat-q4_k_m.gguf /tmp/Modelfile.phogpt
```

## Alternative: Use Docker Volume

### Mount Local Models Directory

If you want to keep GGUF files accessible:

```bash
# Stop current container
docker stop ollama

# Start with volume mount
docker run -d \
  -v ollama:/root/.ollama \
  -v e:/QC_tech/SanViecLam/SanViecLam.Chatbot/convertPhoGPT/models:/models \
  -p 11434:11434 \
  --name ollama \
  ollama/ollama

# Now you can reference local files
docker exec -i ollama sh -c 'cat > /tmp/Modelfile.phogpt' <<'EOF'
FROM /models/phogpt-4b-chat-q4_k_m.gguf
# ... rest of Modelfile
EOF

docker exec ollama ollama create phogpt-4b-chat -f /tmp/Modelfile.phogpt
```

## Update Your Application

### Option A: No Changes (Ollama on localhost)

If your `.env` already has:
```env
OLLAMA_HOST=http://localhost:11434
```

Just update the model name:
```env
LLM_MODEL=phogpt-4b-chat
QWEN_MODEL=phogpt-4b-chat
```

### Option B: Using Docker Network

If your app is also in Docker:

```yaml
# docker-compose.yml
services:
  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama:/root/.ollama

  job_bot:
    build: .
    environment:
      - OLLAMA_HOST=http://ollama:11434
      - LLM_MODEL=phogpt-4b-chat
    depends_on:
      - ollama
```

## Verify Setup

### Check Model Exists

```bash
docker exec ollama ollama list
```

Expected output:
```
NAME                    ID          SIZE    MODIFIED
phogpt-4b-chat:latest   abc123...   2.4GB   2 minutes ago
```

### Test API

```bash
curl http://localhost:11434/api/tags
```

Should include `phogpt-4b-chat` in the list.

### Test Chat

```bash
curl -X POST http://localhost:11434/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "phogpt-4b-chat",
    "messages": [
      {"role": "user", "content": "Tìm việc kỹ sư phần mềm tại Hà Nội"}
    ],
    "stream": false
  }'
```

## Troubleshooting

### Model Not Found After Creation

```bash
# Check if model exists
docker exec ollama ollama list

# If missing, check logs
docker logs ollama

# Try recreating
docker exec ollama ollama create phogpt-4b-chat -f /tmp/Modelfile.phogpt
```

### Permission Denied

```bash
# Ensure Docker has permissions
docker exec -u root ollama ls -la /tmp/
```

### Out of Disk Space

```bash
# Check Docker disk usage
docker system df

# Clean up unused images/containers
docker system prune -a

# Check Ollama volume
docker exec ollama du -sh /root/.ollama
```

### API Connection Refused

```bash
# Check if Ollama is responding
curl http://localhost:11434/api/tags

# Check container status
docker ps | grep ollama

# Check container logs
docker logs ollama --tail 50
```

## Persistence

Models created in Docker are stored in the `ollama` volume:

```bash
# View volume
docker volume ls | grep ollama

# Inspect volume
docker volume inspect ollama

# Backup volume (optional)
docker run --rm -v ollama:/data -v $(pwd):/backup alpine tar czf /backup/ollama-backup.tar.gz -C /data .

# Restore volume (optional)
docker run --rm -v ollama:/data -v $(pwd):/backup alpine tar xzf /backup/ollama-backup.tar.gz -C /data
```

## Summary

| Step | Command | Status |
|------|---------|--------|
| 1. Download GGUF | `huggingface-cli download ...` | ✅ Local |
| 2. Copy to Docker | `docker cp ... ollama:/tmp/` | ✅ In container |
| 3. Create Modelfile | `docker exec ... cat > /tmp/Modelfile` | ✅ In container |
| 4. Create model | `docker exec ollama ollama create ...` | ✅ Persistent |
| 5. Test | `docker exec ollama ollama run ...` | ✅ Works |
| 6. Use in app | Update `LLM_MODEL` in `.env` | ✅ Ready |

The model persists in the `ollama` Docker volume, so it survives container restarts!
