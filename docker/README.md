# Docker Deployment Guide - Phase 1 Optimized

This guide covers deploying the chatbot application with **Phase 1 optimizations** using Docker Compose.

## What's Included

The Docker Compose setup includes:

1. **PostgreSQL** (pgvector) - Database with vector extension

   - Configured with `max_connections=200`
   - Persistent volume for data

2. **Redis** - Caching layer (Phase 1 Optimization)

   - 256MB memory limit
   - LRU eviction policy
   - AOF persistence enabled
   - Persistent volume for data

3. **Backend (FastAPI)** - Application server

   - Phase 1 optimizations enabled
   - Database pool: 150 connections
   - Redis caching enabled
   - Rate limiting: 30 queries/min, 10 uploads/min

4. **Frontend** (Optional) - React SPA
5. **Nginx** (Optional) - Reverse proxy for production

## Phase 1 Optimizations Enabled

- ✅ Database connection pool: 30 → 150
- ✅ Redis caching: 40× faster cached queries
- ✅ **Semantic caching**: Catches similar queries ("What is Python?" = "What's Python?")
- ✅ Rate limiting: Protection against overload
- ✅ LRU embedding cache: 1000 most frequent queries
- ✅ PostgreSQL max_connections: 200

## Quick Start

### 1. Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- Google Gemini API Key

### 2. Configuration

```bash
cd docker
cp .env.example .env
```

Edit `.env` and set your Google API key:

```bash
GOOGLE_API_KEY=your_actual_api_key_here
```

### 3. Start Services

**Option A: Backend + Database + Redis (Recommended)**

```bash
docker-compose up -d
```

**Option B: With Frontend Development Server**

```bash
docker-compose --profile dev up -d
```

**Option C: Full Production Stack with Nginx**

```bash
docker-compose --profile production up -d
```

### 4. Verify Services

Check all services are running:

```bash
docker-compose ps
```

Expected output:

```
NAME                  STATUS              PORTS
chatbot-backend       Up (healthy)        0.0.0.0:8000->8000/tcp
chatbot-postgres      Up (healthy)        0.0.0.0:5432->5432/tcp
chatbot-redis         Up (healthy)        0.0.0.0:6379->6379/tcp
```

### 5. Test the Application

**Health Check:**

```bash
curl http://localhost:8000/api/health
```

Expected response:

```json
{
  "status": "healthy",
  "database": "connected",
  "message": "Chatbot API is running"
}
```

**Test Redis Connection:**

```bash
docker exec chatbot-redis redis-cli ping
# Should return: PONG
```

**Test Database Connection:**

```bash
docker exec chatbot-postgres psql -U postgres -d chatbot_db -c "SELECT version();"
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  Client                         │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│         Backend (FastAPI) :8000                 │
│  - Rate Limiting (30/min, 10/min)               │
│  - LRU Embedding Cache (1000 queries)           │
├─────────────────────────────────────────────────┤
│         Redis Cache :6379                       │
│  - 256MB Memory                                 │
│  - LRU Eviction Policy                          │
│  - Query Results Caching (1h TTL)               │
├─────────────────────────────────────────────────┤
│         PostgreSQL + pgvector :5432             │
│  - Connection Pool: 50 + 100 overflow           │
│  - max_connections: 200                         │
│  - Document Storage & Vector Search             │
└─────────────────────────────────────────────────┘
```

## Service Details

### PostgreSQL (chatbot-postgres)

**Configuration:**

- Image: `pgvector/pgvector:pg15`
- Port: `5432`
- Max Connections: `200`
- Health Check: `pg_isready` every 10s
- Volume: `postgres_data` (persistent)

**Access Database:**

```bash
docker exec -it chatbot-postgres psql -U postgres -d chatbot_db
```

### Redis (chatbot-redis)

**Configuration:**

- Image: `redis:7-alpine`
- Port: `6379`
- Memory Limit: `256MB`
- Eviction Policy: `allkeys-lru`
- Persistence: AOF (append-only file)
- Health Check: `redis-cli ping` every 10s
- Volume: `redis_data` (persistent)
- **Semantic Caching:** Enabled by default (similarity threshold: 0.95)

**Access Redis CLI:**

```bash
docker exec -it chatbot-redis redis-cli
```

**Check Cache Statistics:**

```bash
docker exec chatbot-redis redis-cli INFO stats
```

**How Semantic Caching Works:**

Semantic caching uses embeddings to match similar queries:

1. **Exact Match First:** Checks for identical query (fastest)
2. **Semantic Match:** If no exact match, compares query embeddings
3. **Similarity Threshold:** Returns cached results if similarity ≥ 0.95

**Example:**
- User queries: "What is Python?"
- Cache stores: query + embedding
- Later query: "What's Python?"
- Semantic match: 97% similar → Cache HIT!
- Result: Instant response without LLM/database call

**Configuration:**
```bash
REDIS_SEMANTIC_CACHE=true          # Enable/disable semantic caching
REDIS_SEMANTIC_THRESHOLD=0.95      # Similarity threshold (0.0-1.0)
CACHE_EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2  # Model name
```

### Backend (chatbot-backend)

**Environment Variables:**

```bash
# Database
DB_HOST=postgres
DB_POOL_SIZE=50
DB_MAX_OVERFLOW=100
DB_POOL_TIMEOUT=60

# Redis
REDIS_ENABLED=true
REDIS_HOST=redis
REDIS_PORT=6379

# API
GOOGLE_API_KEY=<from .env>
```

**View Logs:**

```bash
docker-compose logs -f backend
```

**Access Container:**

```bash
docker exec -it chatbot-backend bash
```

## Performance Monitoring

### 1. Database Connection Pool Usage

```bash
docker exec chatbot-postgres psql -U postgres -d chatbot_db -c \
  "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"
```

### 2. Redis Cache Hit Rate

```bash
docker exec chatbot-redis redis-cli INFO stats | grep keyspace
```

Expected output:

```
keyspace_hits:450
keyspace_misses:150
```

Hit rate calculation: `450 / (450 + 150) = 75%`

### 3. Redis Memory Usage

```bash
docker exec chatbot-redis redis-cli INFO memory | grep used_memory_human
```

### 4. Container Resource Usage

```bash
docker stats chatbot-backend chatbot-postgres chatbot-redis
```

## Scaling & Performance

### Vertical Scaling

**Increase Redis Memory:**

```yaml
# In docker-compose.yml
command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
```

**Increase Database Pool:**

```bash
# In .env
DB_POOL_SIZE=100
DB_MAX_OVERFLOW=200
```

Update PostgreSQL:

```yaml
# In docker-compose.yml
command:
  - "postgres"
  - "-c"
  - "max_connections=400"
```

### Horizontal Scaling

**Multiple Backend Instances:**

```bash
docker-compose up -d --scale backend=3
```

**Note:** Requires:

1. Load balancer (Nginx/HAProxy)
2. Shared Redis instance
3. Shared PostgreSQL instance

## Maintenance

### Backup Data

**Backup PostgreSQL:**

```bash
docker exec chatbot-postgres pg_dump -U postgres chatbot_db > backup.sql
```

**Backup Redis:**

```bash
docker exec chatbot-redis redis-cli SAVE
docker cp chatbot-redis:/data/dump.rdb redis-backup.rdb
```

### Restore Data

**Restore PostgreSQL:**

```bash
cat backup.sql | docker exec -i chatbot-postgres psql -U postgres -d chatbot_db
```

**Restore Redis:**

```bash
docker cp redis-backup.rdb chatbot-redis:/data/dump.rdb
docker-compose restart redis
```

### Clear Cache

**Clear Redis Cache:**

```bash
docker exec chatbot-redis redis-cli FLUSHDB
```

**Clear All Data:**

```bash
docker-compose down -v  # ⚠️ This deletes all volumes!
```

### Update Services

**Pull Latest Images:**

```bash
docker-compose pull
```

**Rebuild Backend:**

```bash
docker-compose build --no-cache backend
docker-compose up -d backend
```

**Restart All Services:**

```bash
docker-compose restart
```

## Troubleshooting

### Backend Can't Connect to Redis

**Check Redis is Running:**

```bash
docker-compose ps redis
```

**Check Redis Health:**

```bash
docker exec chatbot-redis redis-cli ping
```

**View Redis Logs:**

```bash
docker-compose logs redis
```

**Solution:** Ensure Redis is healthy before backend starts. The `depends_on` with health checks should handle this.

### Database Connection Pool Exhausted

**Check Active Connections:**

```bash
docker exec chatbot-postgres psql -U postgres -d chatbot_db -c \
  "SELECT count(*) FROM pg_stat_activity;"
```

**Solution:**

1. Increase `DB_POOL_SIZE` and `DB_MAX_OVERFLOW` in `.env`
2. Increase PostgreSQL `max_connections`
3. Restart services: `docker-compose restart backend postgres`

### Out of Memory Errors

**Check Container Memory:**

```bash
docker stats --no-stream
```

**Solution:**

1. Increase Docker Desktop memory limit
2. Add memory limits to docker-compose.yml:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 4G
```

### Rate Limit Too Restrictive

**Temporary Disable:**
Set in backend code or rebuild with adjusted limits.

**Permanent Adjustment:**
Edit `src/routers/chatbot.py` and rebuild:

```bash
docker-compose build backend
docker-compose up -d backend
```

## Environment Variables Reference

| Variable                    | Default                                      | Description                                |
| --------------------------- | -------------------------------------------- | ------------------------------------------ |
| `GOOGLE_API_KEY`            | -                                            | **Required** Gemini API key                |
| `DB_NAME`                   | `chatbot_db`                                 | Database name                              |
| `DB_USER`                   | `postgres`                                   | Database user                              |
| `DB_PASSWORD`               | `postgres`                                   | Database password                          |
| `DB_PORT`                   | `5432`                                       | Database port                              |
| `DB_POOL_SIZE`              | `50`                                         | Base connection pool size                  |
| `DB_MAX_OVERFLOW`           | `100`                                        | Max overflow connections                   |
| `DB_POOL_TIMEOUT`           | `60`                                         | Connection timeout (seconds)               |
| `DB_POOL_RECYCLE`           | `3600`                                       | Connection recycle time (seconds)          |
| `REDIS_ENABLED`             | `true`                                       | Enable/disable Redis caching               |
| `REDIS_PORT`                | `6379`                                       | Redis port                                 |
| `REDIS_DB`                  | `0`                                          | Redis database number                      |
| `REDIS_PASSWORD`            | -                                            | Redis password (optional)                  |
| `REDIS_SEMANTIC_CACHE`      | `true`                                       | Enable semantic similarity cache matching  |
| `REDIS_SEMANTIC_THRESHOLD`  | `0.95`                                       | Similarity threshold (0.0-1.0, stricter→1) |
| `CACHE_EMBEDDING_MODEL`     | `paraphrase-multilingual-MiniLM-L12-v2`      | Embedding model for semantic cache         |

## Production Deployment

### Security Hardening

1. **Change Default Passwords:**

```bash
# In .env
DB_PASSWORD=<strong-random-password>
REDIS_PASSWORD=<strong-random-password>
```

Update docker-compose.yml:

```yaml
redis:
  command: redis-server --requirepass ${REDIS_PASSWORD} --appendonly yes ...
```

2. **Remove Port Exposure:**

```yaml
postgres:
  # Remove or comment out
  # ports:
  #   - "5432:5432"

redis:
  # Remove or comment out
  # ports:
  #   - "6379:6379"
```

3. **Enable SSL/TLS:**
   Use Nginx with SSL certificates (see `nginx` service in docker-compose.yml).

4. **Use Docker Secrets:**
   For sensitive data in Swarm mode.

### High Availability

**Redis Sentinel (Master-Slave):**

```yaml
redis-master:
  image: redis:7-alpine
  # ...

redis-replica:
  image: redis:7-alpine
  command: redis-server --replicaof redis-master 6379
  # ...

redis-sentinel:
  image: redis:7-alpine
  command: redis-sentinel /etc/redis/sentinel.conf
  # ...
```

**PostgreSQL Replication:**
Use PostgreSQL streaming replication or pgpool-II.

## Performance Benchmarks

### Expected Performance (Phase 1 Optimized)

| Metric                       | Value         |
| ---------------------------- | ------------- |
| Max Concurrent Connections   | 150           |
| Cached Query Response Time   | 50ms          |
| Uncached Query Response Time | 1800-2000ms   |
| Cache Hit Rate               | 30-50%        |
| Queries/Minute (mixed)       | 45-60         |
| Queries/Minute (cached only) | 1200+         |
| Rate Limit (Chat)            | 30/min per IP |
| Rate Limit (Upload)          | 10/min per IP |

### Stress Testing

**Load Test with Apache Bench:**

```bash
# Install ab (apache2-utils)
apt-get install apache2-utils

# Test 100 requests, 10 concurrent
ab -n 100 -c 10 -p query.json -T application/json \
  http://localhost:8000/api/chatbot/chat
```

**Monitor During Load:**

```bash
# Terminal 1: Container stats
docker stats

# Terminal 2: Backend logs
docker-compose logs -f backend

# Terminal 3: Redis stats
watch -n 1 'docker exec chatbot-redis redis-cli INFO stats | grep keyspace'
```

## Next Steps

After successful Phase 1 deployment:

1. **Monitor Performance:** Track cache hit rates, connection pool usage
2. **Tune Settings:** Adjust rate limits and pool sizes based on actual usage
3. **Plan Phase 2:** Async document processing with background workers
4. **Plan Phase 3:** Service separation for true horizontal scalability

## Support

- **Documentation:** [phase1_implementation_summary.md](../docs/evaluations/phase1_implementation_summary.md)
- **Issues:** Check Docker logs and health checks
- **Performance:** Monitor with `docker stats` and application metrics

---

**Docker Deployment Guide - Phase 1 Optimized**
**Last Updated:** November 3, 2025
