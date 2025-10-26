# Quick Fix: Enable pgvector

## Current Error
```
ERROR: extension "vector" is not available
Could not open extension control file "/usr/share/postgresql/15/extension/vector.control"
```

## Solution Options

### Option 1: Restart Docker with pgvector image (Easiest)

If you're using Docker, update and restart:

```bash
cd docker

# Stop and remove old PostgreSQL container
docker-compose stop postgres
docker-compose rm -f postgres

# Start with new pgvector image
docker-compose up -d postgres

# Wait for it to be ready
sleep 5

# Enable the extension
docker exec -i chatbot-postgres psql -U root -d CHATBOT_OCR_DB -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Option 2: Use Postgres with ANKANE/pgvector (Alternative)

Update `docker/docker-compose.yml` to use:
```yaml
image: ankane/pgvector:latest
```
instead of the current image.

### Option 3: Install pgvector on your PostgreSQL server

If you're NOT using Docker and have PostgreSQL installed directly:

**Ubuntu/Debian:**
```bash
sudo apt-get install postgresql-15-pgvector
sudo systemctl restart postgresql
```

**macOS:**
```bash
brew install pgvector
```

Then run:
```bash
psql -U root -d CHATBOT_OCR_DB -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

## Recommended: Quick Docker Restart

```bash
cd docker && docker-compose down postgres && docker-compose up -d postgres
```

Then verify:
```bash
docker exec -i chatbot-postgres psql -U root -d CHATBOT_OCR_DB -c "\dx vector"
```

