# Shell Scripts Guide - RAG Chatbot v2.0

## Overview

This guide explains the shell scripts created for managing the RAG Chatbot project lifecycle.

**Two versions available:**
- **Bash scripts (.sh)** - For Linux, macOS, and Windows Git Bash
- **Batch files (.bat)** - For Windows Command Prompt

### Bash Scripts (Linux/macOS/Git Bash)

1. **[setup.sh](../setup.sh)** - First-time project setup
2. **[dev.sh](../dev.sh)** - Development mode with hot-reload
3. **[prod.sh](../prod.sh)** - Production deployment with Docker

### Windows Batch Files (Command Prompt)

1. **[setup.bat](../setup.bat)** - First-time project setup
2. **[dev.bat](../dev.bat)** - Development mode with hot-reload
3. **[prod.bat](../prod.bat)** - Production deployment with Docker

**Note:** Both versions have identical functionality. Use .bat files for native Windows Command Prompt, or .sh files with Git Bash on Windows.

---

## 1. setup.sh - Project Setup Script

### Purpose
Automates first-time project setup on any platform (Windows/Linux/macOS).

### What It Does

1. **Detects Operating System**
   - Windows (Git Bash/MSYS)
   - Linux
   - macOS

2. **Checks Prerequisites**
   - Python 3.10+
   - Node.js (optional for frontend)
   - Docker (optional for containerized deployment)
   - Git

3. **Creates Virtual Environment**
   - Creates `.venv` directory
   - Handles Windows/Unix path differences

4. **Installs Python Dependencies**
   - Upgrades pip
   - Installs all packages from requirements.txt
   - Handles flash-attn exclusion (Windows compatibility)

5. **Sets Up Environment File**
   - Copies .env.example to .env
   - Prompts user to configure API keys
   - Lists required configuration

6. **Creates Project Directories**
   - data/faiss
   - data/uploads
   - logs

7. **Sets Up PostgreSQL (Optional)**
   - Starts PostgreSQL via Docker Compose
   - Waits for database to be ready

8. **Checks Tesseract OCR**
   - Verifies Tesseract installation
   - Checks for Vietnamese language pack
   - Provides platform-specific installation instructions

9. **Initializes Database (Optional)**
   - Runs Alembic migrations
   - Creates database schema

10. **Sets Up Frontend (Optional)**
    - Installs npm dependencies
    - Configures React development server

### Usage

```bash
# Make script executable (Linux/Mac)
chmod +x setup.sh

# Run setup
./setup.sh
```

**On Windows (Git Bash):**
```bash
bash setup.sh
```

### First Run Checklist

After running setup.sh:

- [ ] Edit `.env` and add your `GOOGLE_API_KEY`
- [ ] Configure `JWT_SECRET_KEY` (generate with: `python -c "import secrets; print(secrets.token_urlsafe(32))"`)
- [ ] Ensure PostgreSQL is running
- [ ] For OCR support, install Tesseract if not already installed

---

## 2. dev.sh - Development Mode Script

### Purpose
Runs the project in development mode with hot-reload for rapid development.

### What It Does

1. **Activates Virtual Environment**
   - Handles Windows/Unix differences
   - Exits if .venv not found

2. **Validates Environment**
   - Checks .env file exists
   - Validates GOOGLE_API_KEY is configured

3. **Checks PostgreSQL Connection**
   - Uses pg_isready if available
   - Auto-starts PostgreSQL via Docker if not running

4. **Shows Development Info**
   - Displays enabled features from .env
   - Shows hot-reload status
   - Lists access URLs

5. **Starts Backend with Hot-Reload**
   - Runs uvicorn with --reload flag
   - Watches src directory for changes
   - Available at http://localhost:8000
   - API docs at http://localhost:8000/docs

6. **Optionally Starts Frontend**
   - Prompts user to start frontend
   - Runs npm run dev in background
   - Available at http://localhost:3000

7. **Handles Cleanup**
   - Traps Ctrl+C signal
   - Gracefully stops all servers
   - Cleans up PID files

### Usage

```bash
# Start both backend and frontend (interactive)
./dev.sh

# Start only backend
./dev.sh backend

# Start only frontend
./dev.sh frontend
```

### Development Workflow

1. **First time:**
   ```bash
   ./setup.sh  # Run once
   ```

2. **Daily development:**
   ```bash
   ./dev.sh    # Start servers
   # Edit code - changes auto-reload
   # Ctrl+C to stop
   ```

3. **Backend changes:**
   - Edit files in `src/`
   - Server automatically restarts
   - Check terminal for errors

4. **Frontend changes:**
   - Edit files in `frontend/app/src/`
   - Browser auto-refreshes
   - Check browser console for errors

### Features Displayed

The script shows which RAG v2.0 features are enabled:

- **Semantic Chunking** (USE_LANGCHAIN_CHUNKING)
- **OCR Processing** (OCR_ENABLED)
- **FAISS Acceleration** (USE_FAISS)
- **Multi-Query Retrieval** (MULTI_QUERY_ENABLED)

Edit `.env` to enable/disable features.

---

## 3. prod.sh - Production Deployment Script

### Purpose
Manages production deployment using Docker containers.

### What It Does

1. **Checks Prerequisites**
   - Verifies Docker installation
   - Verifies Docker Compose installation
   - Shows versions

2. **Validates Environment**
   - Checks .env file exists
   - Validates critical variables (GOOGLE_API_KEY, JWT_SECRET_KEY)

3. **Builds Docker Images**
   - Builds backend container
   - Builds frontend container (optional)
   - Supports --no-cache flag

4. **Starts Services**
   - PostgreSQL with pgvector
   - Backend (FastAPI with Gunicorn)
   - Frontend (optional, with --profile dev)

5. **Manages Database**
   - Runs migrations
   - Creates backups
   - Restores from backups

6. **Monitors Services**
   - Shows container status
   - Displays logs
   - Shows access points

### Usage

```bash
# Start production environment
./prod.sh start

# Stop all services
./prod.sh stop

# Restart services
./prod.sh restart

# Rebuild images (after code changes)
./prod.sh rebuild

# Show logs
./prod.sh logs

# Show service status
./prod.sh status

# Run database migrations
./prod.sh migrate

# Create database backup
./prod.sh backup

# Restore database from backup
./prod.sh restore

# Show production configuration
./prod.sh info

# Open shell in backend container
./prod.sh shell
```

### Production Commands Reference

#### Start Services

```bash
./prod.sh start
```

Prompts whether to include frontend container.

**Services started:**
- PostgreSQL (port 5432)
- Backend API (port 8000)
- Frontend (port 3000, optional)

#### Stop Services

```bash
./prod.sh stop
```

Gracefully stops all containers.

#### Rebuild After Code Changes

```bash
./prod.sh rebuild
```

Rebuilds Docker images with --no-cache and restarts services.

#### View Logs

```bash
./prod.sh logs
```

Shows last 100 lines and follows new logs (Ctrl+C to exit).

#### Check Status

```bash
./prod.sh status
```

Shows:
- Running containers
- Access URLs
- Service health

#### Database Operations

**Run migrations:**
```bash
./prod.sh migrate
```

**Create backup:**
```bash
./prod.sh backup
```

Creates timestamped backup in `backups/` directory.

**Restore backup:**
```bash
./prod.sh restore
```

Lists available backups and prompts for selection.

#### Container Shell Access

```bash
./prod.sh shell
```

Opens bash shell in backend container for debugging.

### Production Configuration

The script shows production-specific settings:

**Services:**
- Backend (FastAPI with Gunicorn)
- PostgreSQL with pgvector extension
- Frontend (optional)

**Optimizations:**
- Gunicorn workers: 4
- DB connection pool: 50 (max 100)
- Auto-restart on failure
- Health checks enabled

**Features (from .env):**
- Semantic Chunking status
- OCR status
- FAISS acceleration status
- Multi-Query status

### Access Points

After starting production services:

- **API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **PostgreSQL:** localhost:5432
- **Frontend:** http://localhost:3000 (if enabled)

---

## Platform-Specific Notes

### Windows (Command Prompt with .bat files)

1. **Run batch files:**
   ```cmd
   setup.bat
   dev.bat
   prod.bat start
   ```

2. **Features:**
   - Native Windows batch scripts
   - Colored output (Windows 10+)
   - Automatic virtual environment activation
   - Interactive prompts

3. **Docker Desktop required:**
   - Install from https://docs.docker.com/desktop/install/windows-install/

4. **Tesseract OCR:**
   - Download installer from https://github.com/UB-Mannheim/tesseract/wiki
   - Add to PATH during installation

5. **Note on colors:**
   - ANSI colors work on Windows 10+ Command Prompt
   - Windows Terminal recommended for best experience

### Windows (Git Bash with .sh files)

1. **Run scripts:**
   ```bash
   bash setup.sh
   bash dev.sh
   bash prod.sh start
   ```

2. **Virtual environment activation:**
   - Scripts automatically use `.venv/Scripts/activate`

3. **Docker Desktop required:**
   - Install from https://docs.docker.com/desktop/install/windows-install/

4. **Tesseract OCR:**
   - Download installer from https://github.com/UB-Mannheim/tesseract/wiki
   - Add to PATH

5. **Choosing between .bat and .sh:**
   - Use .bat for native Command Prompt
   - Use .sh for Git Bash (if you prefer bash syntax)
   - Both have identical functionality

### Linux

1. **Make scripts executable:**
   ```bash
   chmod +x setup.sh dev.sh prod.sh
   ```

2. **Install Tesseract:**
   ```bash
   sudo apt-get update
   sudo apt-get install tesseract-ocr tesseract-ocr-eng tesseract-ocr-vie
   ```

3. **Install Docker:**
   ```bash
   # Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh

   # Docker Compose
   sudo apt-get install docker-compose
   ```

### macOS

1. **Make scripts executable:**
   ```bash
   chmod +x setup.sh dev.sh prod.sh
   ```

2. **Install Tesseract:**
   ```bash
   brew install tesseract tesseract-lang
   ```

3. **Install Docker:**
   - Download Docker Desktop from https://docs.docker.com/desktop/install/mac-install/

---

## Troubleshooting

### "Virtual environment not found"

**Problem:** Running dev.sh without setup
**Solution:** Run `./setup.sh` first

### "GOOGLE_API_KEY not configured"

**Problem:** .env file not edited
**Solution:**
```bash
nano .env  # Edit file
# Add: GOOGLE_API_KEY=your_actual_key_here
```

### "Cannot connect to PostgreSQL"

**Problem:** PostgreSQL not running
**Solution:**
```bash
cd docker
docker-compose up -d postgres
cd ..
```

### "Docker not found"

**Problem:** Docker not installed
**Solution:** Install Docker Desktop for your platform

### "Permission denied: ./setup.sh"

**Problem:** Script not executable (Linux/Mac)
**Solution:**
```bash
chmod +x setup.sh dev.sh prod.sh
```

### "Tesseract not found"

**Problem:** Tesseract OCR not installed
**Solution:**
- **Windows:** Download from https://github.com/UB-Mannheim/tesseract/wiki
- **Linux:** `sudo apt-get install tesseract-ocr tesseract-ocr-vie`
- **macOS:** `brew install tesseract tesseract-lang`

Or disable OCR in .env:
```bash
OCR_ENABLED=false
```

### "Port 8000 already in use"

**Problem:** Another service using port 8000
**Solution:**
```bash
# Find process using port
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows

# Kill process or change port in .env
API_PORT=8001
```

---

## Typical Workflows

### Initial Setup (First Time)

**Linux/macOS/Git Bash:**
```bash
# 1. Clone repository
git clone <repo-url>
cd Chatbot

# 2. Run setup
./setup.sh

# 3. Configure environment
nano .env
# Add GOOGLE_API_KEY and JWT_SECRET_KEY

# 4. Start development
./dev.sh
```

**Windows Command Prompt:**
```cmd
REM 1. Clone repository
git clone <repo-url>
cd Chatbot

REM 2. Run setup
setup.bat

REM 3. Configure environment
notepad .env
REM Add GOOGLE_API_KEY and JWT_SECRET_KEY

REM 4. Start development
dev.bat
```

### Daily Development

**Linux/macOS/Git Bash:**
```bash
# Start servers
./dev.sh

# Edit code
# - Backend: src/
# - Frontend: frontend/app/src/

# Changes auto-reload

# Stop servers
# Ctrl+C
```

**Windows Command Prompt:**
```cmd
REM Start servers
dev.bat

REM Edit code
REM - Backend: src/
REM - Frontend: frontend/app/src/

REM Changes auto-reload

REM Stop servers
REM Ctrl+C
```

### Testing Production Build

```bash
# Build and start
./prod.sh start

# Check status
./prod.sh status

# View logs
./prod.sh logs

# Stop
./prod.sh stop
```

### Database Operations

```bash
# Create backup before changes
./prod.sh backup

# Make changes (upload documents, etc.)

# If something goes wrong, restore
./prod.sh restore
```

### Deploying Code Changes

```bash
# 1. Pull latest code
git pull

# 2. Rebuild containers
./prod.sh rebuild

# 3. Run migrations if needed
./prod.sh migrate

# 4. Check status
./prod.sh status
```

### Migrating Existing Documents

```bash
# 1. Activate virtual environment
source .venv/bin/activate  # Linux/Mac
source .venv/Scripts/activate  # Windows

# 2. Run migration script (dry-run first)
python scripts/migrate_to_langchain_chunks.py --dry-run

# 3. Backup database
./prod.sh backup

# 4. Run actual migration
python scripts/migrate_to_langchain_chunks.py

# 5. Verify
python scripts/migrate_to_langchain_chunks.py --status
```

---

## Environment Variables Reference

### Required

- `GOOGLE_API_KEY` - Google Gemini API key
- `JWT_SECRET_KEY` - Secret key for JWT authentication

### Database

- `DB_HOST` - Database host (default: localhost)
- `DB_PORT` - Database port (default: 5432)
- `DB_NAME` - Database name (default: chatbot_db)
- `DB_USER` - Database user (default: postgres)
- `DB_PASSWORD` - Database password

### RAG Features (v2.0)

- `USE_LANGCHAIN_CHUNKING` - Enable semantic chunking (default: true)
- `CHUNK_SIZE` - Chunk size in characters (default: 1500)
- `CHUNK_OVERLAP` - Overlap between chunks (default: 200)
- `USE_FAISS` - Enable FAISS acceleration (default: false)
- `MULTI_QUERY_ENABLED` - Enable multi-query retrieval (default: true)
- `OCR_ENABLED` - Enable Tesseract OCR (default: true)
- `OCR_LANGUAGES` - OCR languages (default: vie+eng)

See [.env.example](../.env.example) for complete list.

---

## Performance Tips

### Development Mode

1. **Disable unused features** in .env to speed up processing:
   ```bash
   USE_FAISS=false          # If not testing search performance
   MULTI_QUERY_ENABLED=false  # If not testing query variations
   OCR_ENABLED=false        # If not testing scanned PDFs
   ```

2. **Use smaller chunk sizes** for faster processing:
   ```bash
   CHUNK_SIZE=500
   CHUNK_OVERLAP=50
   ```

3. **Reduce logging** for cleaner output:
   ```bash
   LOG_LEVEL=ERROR
   ```

### Production Mode

1. **Enable all optimizations**:
   ```bash
   USE_FAISS=true
   MULTI_QUERY_ENABLED=true
   USE_LANGCHAIN_CHUNKING=true
   ```

2. **Tune Gunicorn workers** (in DockerFile):
   - Set to 2x CPU cores for CPU-bound tasks
   - Current: 4 workers

3. **Database connection pooling** (in .env):
   ```bash
   DB_POOL_SIZE=50
   DB_MAX_OVERFLOW=100
   ```

4. **Monitor resources**:
   ```bash
   ./prod.sh status
   docker stats  # Real-time resource usage
   ```

---

## Security Notes

### Development

- `.env` file contains secrets - **never commit to Git**
- Hot-reload exposes server on 0.0.0.0 - **only use on trusted networks**

### Production

- Change default database passwords in .env
- Use strong JWT_SECRET_KEY (32+ characters)
- Enable HTTPS in production (configure reverse proxy)
- Restrict PostgreSQL port (5432) to localhost or VPN
- Regular database backups: `./prod.sh backup`

---

## Next Steps

After setting up with these scripts:

1. **Read User Guide:** [RAG_ENHANCEMENTS_README.md](RAG_ENHANCEMENTS_README.md)
2. **Review Implementation:** [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
3. **Frontend Integration:** [FRONTEND_INTEGRATION_GUIDE.md](FRONTEND_INTEGRATION_GUIDE.md)
4. **Test Features:** Upload PDFs and test chunking, OCR, multi-query
5. **Migrate Documents:** Use migration script for existing documents
6. **Monitor Performance:** Check logs and metrics

---

## Script Maintenance

### Updating Scripts

If you need to modify the scripts:

1. **Edit the .sh file:**
   ```bash
   nano setup.sh  # or dev.sh, prod.sh
   ```

2. **Test thoroughly:**
   ```bash
   bash -n setup.sh  # Check syntax
   ./setup.sh        # Test execution
   ```

3. **Document changes** in this guide

### Adding New Features

To add new features to scripts:

1. Add environment variable to .env.example
2. Update setup.sh to mention new variable
3. Update dev.sh to display feature status
4. Update prod.sh to show in production info
5. Document in this guide

---

## Support

If you encounter issues:

1. **Check logs:**
   ```bash
   ./prod.sh logs        # Production
   # Or check terminal output in dev mode
   ```

2. **Verify environment:**
   ```bash
   ./prod.sh info        # Production config
   # Or check .env file directly
   ```

3. **Review documentation:**
   - This guide
   - [RAG_ENHANCEMENTS_README.md](RAG_ENHANCEMENTS_README.md)
   - [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)

4. **Check prerequisites:**
   - Python 3.10+
   - PostgreSQL running
   - Docker (for production)
   - Tesseract (for OCR)

---

**Document Version:** 1.0
**Last Updated:** 2025-12-06
**Status:** Production Ready
