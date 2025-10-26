# How to Enable pgvector Extension

## Option 1: Using Docker (Recommended)

If you're using Docker, the simplest approach is to use the `pgvector` Docker image.

### Step 1: Update Docker Compose

The `docker-compose.yml` has been updated to use the `pgvector/pgvector:pg15` image which includes the extension pre-installed.

### Step 2: Restart PostgreSQL Container

```bash
cd docker
docker-compose stop postgres
docker-compose rm -f postgres  # Remove old container
docker-compose up -d postgres
```

### Step 3: Verify Installation

```bash
# Connect to the database
docker exec -it chatbot-postgres psql -U postgres -d chatbot_db

# Check if extension is enabled
\dx vector

# Should show:
#                 List of installed extensions
#   Name   | Version |   Schema   |         Description          
# ---------+--------+------------+------------------------------
#  vector  | 0.5.1  | public     | vector data type and ivfflat/hnsw/ac...
```

## Option 2: Manual Installation (Non-Docker)

If you're running PostgreSQL directly on your system:

### On Ubuntu/Debian

```bash
# Install pgvector package
sudo apt-get update
sudo apt-get install postgresql-15-pgvector

# Restart PostgreSQL
sudo systemctl restart postgresql

# Enable the extension
psql -U postgres -d your_database -c "CREATE EXTENSION vector;"
```

### On macOS with Homebrew

```bash
# Install pgvector
brew install pgvector

# Enable the extension
psql -U postgres -d your_database -c "CREATE EXTENSION vector;"
```

### On Windows

1. Download pgvector for Windows from: https://github.com/pgvector/pgvector/releases
2. Copy the files to your PostgreSQL installation directory
3. Enable the extension:
   ```sql
   CREATE EXTENSION vector;
   ```

## Option 3: Quick Enable Script

Run the provided script:

```bash
cd docker
chmod +x enable-pgvector.sh
./enable-pgvector.sh
```

## Verification

After enabling, test the extension:

```bash
psql -U postgres -d your_database -c "
  CREATE TABLE test_vectors (id serial, embedding vector(384));
  INSERT INTO test_vectors (embedding) VALUES ('[0.1,0.2,0.3]'::vector);
  SELECT * FROM test_vectors;
"
```

If this runs without errors, pgvector is working correctly!

## Troubleshooting

### Error: "extension \"vector\" is not available"

**Solution**: Install pgvector on your PostgreSQL server (see Option 2 above)

### Error: "No such file or directory"

**Solution**: You're using a PostgreSQL image without pgvector. Use the updated `docker-compose.yml` with `pgvector/pgvector:pg15` image.

### Permission Denied

**Solution**: Ensure you have superuser privileges:
```sql
ALTER USER your_user WITH SUPERUSER;
```

## Notes

- The pgvector extension must be enabled on **each database** that needs it
- Data is preserved when restarting with a new image
- Always backup your database before major changes

