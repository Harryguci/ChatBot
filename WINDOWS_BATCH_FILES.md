# Windows Batch Files (.bat) Guide

## Quick Start for Windows Users

If you're using Windows Command Prompt (cmd.exe), you can use the `.bat` files instead of the `.sh` shell scripts.

### Available Batch Files

1. **setup.bat** - First-time project setup
2. **dev.bat** - Development mode with hot-reload
3. **prod.bat** - Production deployment with Docker

### Quick Setup (Windows Command Prompt)

```cmd
REM 1. Clone repository
git clone <repo-url>
cd Chatbot

REM 2. Run setup
setup.bat

REM 3. Edit .env and add your API keys
notepad .env

REM 4. Start development
dev.bat
```

## setup.bat - Project Setup

### What It Does

- ✅ Checks Python, Node.js, Docker, Git
- ✅ Creates virtual environment (.venv)
- ✅ Installs Python dependencies
- ✅ Creates .env file from .env.example
- ✅ Creates project directories (data/faiss, data/uploads, logs)
- ✅ Starts PostgreSQL with Docker (optional)
- ✅ Checks Tesseract OCR installation
- ✅ Runs database migrations (optional)
- ✅ Installs frontend dependencies (optional)

### Usage

```cmd
setup.bat
```

### After Setup

1. Edit `.env` file:
   ```cmd
   notepad .env
   ```

2. Add your Google API key:
   ```
   GOOGLE_API_KEY=your_actual_api_key_here
   ```

3. Generate and add JWT secret:
   ```cmd
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
   Copy the output to `JWT_SECRET_KEY` in .env

## dev.bat - Development Mode

### What It Does

- ✅ Activates virtual environment
- ✅ Validates .env configuration
- ✅ Checks PostgreSQL connection
- ✅ Shows enabled features (OCR, FAISS, Multi-Query, etc.)
- ✅ Starts backend with hot-reload (uvicorn --reload)
- ✅ Optionally starts frontend (in new window)
- ✅ Auto-restarts on code changes

### Usage

```cmd
REM Start both backend and frontend (interactive)
dev.bat

REM Start only backend
dev.bat backend

REM Start only frontend
dev.bat frontend
```

### Access Points

- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Frontend:** http://localhost:3000

### Stopping Servers

Press `Ctrl+C` in the command prompt window.

If frontend is running in a separate window, close that window too.

## prod.bat - Production Mode

### What It Does

- ✅ Checks Docker and Docker Compose
- ✅ Validates .env configuration
- ✅ Builds Docker images
- ✅ Starts containers (PostgreSQL, Backend, Frontend)
- ✅ Manages database backups/restores
- ✅ Runs migrations
- ✅ Shows logs and status

### Usage

```cmd
REM Start production environment
prod.bat start

REM Stop all services
prod.bat stop

REM Restart services
prod.bat restart

REM Rebuild images (after code changes)
prod.bat rebuild

REM Show logs
prod.bat logs

REM Show service status
prod.bat status

REM Run database migrations
prod.bat migrate

REM Create database backup
prod.bat backup

REM Restore database from backup
prod.bat restore

REM Show production configuration
prod.bat info

REM Open shell in backend container
prod.bat shell
```

### Production Workflow

1. **First time:**
   ```cmd
   prod.bat start
   ```

2. **After code changes:**
   ```cmd
   prod.bat rebuild
   ```

3. **Backup before major changes:**
   ```cmd
   prod.bat backup
   ```

4. **View logs:**
   ```cmd
   prod.bat logs
   ```

5. **Check status:**
   ```cmd
   prod.bat status
   ```

## Features

### Colored Output

All batch files use ANSI escape codes for colored output:
- 🟢 **Green** - Success messages
- 🟡 **Yellow** - Warnings
- 🔴 **Red** - Errors
- 🔵 **Blue** - Headers
- 🔷 **Cyan** - Information

**Note:** Colors work on Windows 10+ Command Prompt. For best experience, use **Windows Terminal**.

### Interactive Prompts

The batch files ask for confirmation before:
- Recreating virtual environment
- Overwriting .env file
- Starting PostgreSQL
- Running migrations
- Setting up frontend
- Starting frontend in dev mode

### Error Handling

- All critical operations check for errors
- Helpful error messages with solutions
- Automatic fallback to defaults when needed

## Troubleshooting

### "Python not found"

**Solution:**
1. Install Python 3.10+ from https://www.python.org/downloads/
2. During installation, check "Add Python to PATH"
3. Restart Command Prompt

### "Docker not found"

**Solution:**
1. Install Docker Desktop from https://docs.docker.com/desktop/install/windows-install/
2. Restart Command Prompt
3. Ensure Docker Desktop is running

### "Virtual environment not found"

**Solution:**
Run `setup.bat` first before running `dev.bat` or `prod.bat`

### "GOOGLE_API_KEY not configured"

**Solution:**
1. Edit .env file: `notepad .env`
2. Replace `your_google_api_key_here` with your actual API key
3. Get API key from: https://makersuite.google.com/app/apikey

### Colored output not working

**Solution:**
- Update to Windows 10 or later
- Use Windows Terminal instead of legacy cmd.exe
- Or use Git Bash with the `.sh` scripts instead

### "Permission denied" when installing packages

**Solution:**
1. Run Command Prompt as Administrator
2. Or use `--user` flag: Edit setup.bat and change:
   ```cmd
   pip install -r requirements.txt --user
   ```

## Comparison: .bat vs .sh

| Feature | .bat (Command Prompt) | .sh (Git Bash) |
|---------|----------------------|----------------|
| **Windows Native** | ✅ Yes | ❌ Requires Git Bash |
| **Colored Output** | ✅ Yes (Win 10+) | ✅ Yes |
| **Interactive** | ✅ Yes | ✅ Yes |
| **Error Handling** | ✅ Yes | ✅ Yes |
| **Syntax** | Batch script | Bash script |
| **Best For** | Windows Command Prompt users | Users familiar with bash |

**Recommendation:**
- Use `.bat` if you prefer native Windows tools
- Use `.sh` if you're comfortable with Git Bash or coming from Linux/Mac

## Common Commands Reference

### Setup (First Time)

```cmd
setup.bat
notepad .env  REM Configure API keys
```

### Development

```cmd
REM Start servers
dev.bat

REM Start backend only
dev.bat backend

REM Start frontend only
dev.bat frontend
```

### Production

```cmd
REM Start
prod.bat start

REM Stop
prod.bat stop

REM Restart
prod.bat restart

REM Rebuild
prod.bat rebuild

REM Logs
prod.bat logs

REM Status
prod.bat status
```

### Database

```cmd
REM Backup
prod.bat backup

REM Restore
prod.bat restore

REM Migrate
prod.bat migrate
```

## Environment Variables

Edit `.env` file to configure:

```cmd
notepad .env
```

**Required:**
- `GOOGLE_API_KEY` - Your Google Gemini API key
- `JWT_SECRET_KEY` - Secret for JWT authentication

**Optional (with defaults):**
- `USE_LANGCHAIN_CHUNKING=true` - Semantic chunking
- `CHUNK_SIZE=1500` - Chunk size
- `CHUNK_OVERLAP=200` - Chunk overlap
- `OCR_ENABLED=true` - Enable OCR
- `USE_FAISS=false` - FAISS acceleration
- `MULTI_QUERY_ENABLED=true` - Multi-query retrieval

See [.env.example](../env.example) for complete list.

## Next Steps

After running `setup.bat`:

1. ✅ Configure .env file
2. ✅ Start development: `dev.bat`
3. ✅ Upload test documents
4. ✅ Test features (OCR, chunking, search)
5. ✅ Optional: Implement frontend enhancements

## Documentation

For more details:
- **[SHELL_SCRIPTS_GUIDE.md](docs/SHELL_SCRIPTS_GUIDE.md)** - Complete guide (covers both .bat and .sh)
- **[RAG_ENHANCEMENTS_README.md](docs/RAG_ENHANCEMENTS_README.md)** - User guide
- **[PROJECT_DELIVERY_SUMMARY.md](docs/PROJECT_DELIVERY_SUMMARY.md)** - Project overview

## Support

If you encounter issues:

1. Check error messages in the command prompt
2. Review [SHELL_SCRIPTS_GUIDE.md](docs/SHELL_SCRIPTS_GUIDE.md) troubleshooting section
3. Ensure prerequisites are installed (Python, Docker, Tesseract)
4. Check `.env` file is configured correctly

---

**Note:** All three batch files (setup.bat, dev.bat, prod.bat) are production-ready and have identical functionality to their .sh counterparts.

**Last Updated:** 2025-12-06
