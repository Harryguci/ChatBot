# Quick Start - Docker Deployment

## Prerequisites
- Docker & Docker Compose installed
- Google Gemini API key

## Start Application (3 Steps)

### 1. Configure
```bash
cd docker
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
```

### 2. Start Services
```bash
docker-compose up -d
```

### 3. Verify
```bash
# Check services
docker-compose ps

# Test API
curl http://localhost:8000/api/health
```

✅ **Done!** Application running at http://localhost:8000

---

## Common Commands

### Service Management
```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart services
docker-compose restart

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
```

### Monitoring
```bash
# Service status
docker-compose ps

# Resource usage
docker stats

# Backend logs
docker-compose logs -f backend

# Redis stats
docker exec chatbot-redis redis-cli INFO stats

# Database connections
docker exec chatbot-postgres psql -U postgres -d chatbot_db \
  -c "SELECT count(*) FROM pg_stat_activity;"
```

### Maintenance
```bash
# Update and restart
docker-compose pull
docker-compose up -d

# Rebuild backend
docker-compose build backend
docker-compose up -d backend

# Clear Redis cache
docker exec chatbot-redis redis-cli FLUSHDB

# Backup database
docker exec chatbot-postgres pg_dump -U postgres chatbot_db > backup.sql

# Clean up (⚠️ deletes data!)
docker-compose down -v
```

### Access Services
```bash
# Backend shell
docker exec -it chatbot-backend bash

# PostgreSQL CLI
docker exec -it chatbot-postgres psql -U postgres -d chatbot_db

# Redis CLI
docker exec -it chatbot-redis redis-cli
```

---

## Service URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| API | http://localhost:8000 | - |
| Health Check | http://localhost:8000/api/health | - |
| PostgreSQL | localhost:5432 | postgres/postgres |
| Redis | localhost:6379 | - |

---

## Troubleshooting

### Services not starting?
```bash
# Check logs
docker-compose logs

# Check individual service
docker-compose logs backend
```

### Can't connect to database?
```bash
# Ensure database is healthy
docker-compose ps postgres

# Check database logs
docker-compose logs postgres
```

### Redis connection failed?
```bash
# Check Redis is running
docker exec chatbot-redis redis-cli ping

# Should return: PONG
```

### Need to reset everything?
```bash
# Stop and remove all data (⚠️ destructive!)
docker-compose down -v

# Start fresh
docker-compose up -d
```

---

## Performance Indicators

### Check Cache Hit Rate
```bash
docker exec chatbot-redis redis-cli INFO stats | grep keyspace
```

Good hit rate: >40%

### Check Database Connections
```bash
docker exec chatbot-postgres psql -U postgres -d chatbot_db \
  -c "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"
```

Healthy: <150 active connections

### Check Memory Usage
```bash
docker stats --no-stream
```

---

## Phase 1 Optimizations Active

✅ Database pool: 150 connections (50 + 100 overflow)
✅ Redis caching: 40× faster cached queries
✅ Rate limiting: 30 queries/min, 10 uploads/min
✅ LRU cache: 1000 query embeddings
✅ PostgreSQL max_connections: 200

**Expected:** 2-3× query throughput improvement

---

For detailed documentation, see [README.md](./README.md)
