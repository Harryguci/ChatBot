#!/bin/bash

# ===================================================================
# RAG Chatbot - Development Mode Runner
# ===================================================================
# This script runs the project in development mode with hot-reload
# ===================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Print functions
print_header() {
    echo -e "\n${BLUE}================================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}================================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ $1${NC}"
}

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        OS_TYPE="windows"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS_TYPE="linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS_TYPE="mac"
    else
        OS_TYPE="unknown"
    fi
}

# Activate virtual environment
activate_venv() {
    if [ ! -d ".venv" ]; then
        print_error "Virtual environment not found!"
        print_info "Run './setup.sh' first to set up the project"
        exit 1
    fi

    print_info "Activating virtual environment..."

    if [ "$OS_TYPE" = "windows" ]; then
        source .venv/Scripts/activate
    else
        source .venv/bin/activate
    fi

    print_success "Virtual environment activated"
}

# Check .env file
check_env() {
    if [ ! -f ".env" ]; then
        print_warning ".env file not found"
        print_info "Creating from .env.example..."
        cp .env.example .env
        print_warning "Please edit .env and add your API keys before running!"
        exit 1
    fi

    # Check if GOOGLE_API_KEY is set
    if grep -q "GOOGLE_API_KEY=your_google_api_key_here" .env; then
        print_error "GOOGLE_API_KEY not configured in .env"
        print_info "Please edit .env and add your Google API key"
        print_info "Get it from: https://makersuite.google.com/app/apikey"
        exit 1
    fi

    print_success ".env file configured"
}

# Check PostgreSQL
check_postgres() {
    print_info "Checking PostgreSQL connection..."

    # Get DB config from .env
    DB_HOST=$(grep "^DB_HOST=" .env | cut -d'=' -f2)
    DB_PORT=$(grep "^DB_PORT=" .env | cut -d'=' -f2)

    DB_HOST=${DB_HOST:-localhost}
    DB_PORT=${DB_PORT:-5432}

    # Try to connect
    if command -v pg_isready &> /dev/null; then
        if pg_isready -h "$DB_HOST" -p "$DB_PORT" &> /dev/null; then
            print_success "PostgreSQL is running at $DB_HOST:$DB_PORT"
        else
            print_warning "Cannot connect to PostgreSQL at $DB_HOST:$DB_PORT"
            print_info "Starting PostgreSQL with Docker..."

            if command -v docker &> /dev/null; then
                cd docker
                docker-compose up -d postgres
                cd ..
                sleep 3
                print_success "PostgreSQL started"
            else
                print_error "Docker not found. Please start PostgreSQL manually"
                exit 1
            fi
        fi
    else
        print_warning "pg_isready not found. Assuming PostgreSQL is running..."
    fi
}

# Start backend
start_backend() {
    print_header "Starting Backend (Development Mode)"

    print_info "Starting FastAPI server with hot-reload..."
    print_info "API will be available at: ${GREEN}http://localhost:8000${NC}"
    print_info "API Docs at: ${GREEN}http://localhost:8000/docs${NC}"
    print_info ""
    print_warning "Press Ctrl+C to stop"
    print_info ""

    # Run uvicorn with reload
    export PYTHONPATH="${PYTHONPATH}:./src"

    uvicorn src.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --reload \
        --reload-dir src \
        --log-level info
}

# Start frontend (separate terminal)
start_frontend() {
    if [ ! -d "frontend/app" ]; then
        print_warning "Frontend directory not found. Skipping"
        return
    fi

    if ! command -v node &> /dev/null; then
        print_warning "Node.js not found. Skipping frontend"
        return
    fi

    print_header "Starting Frontend (Development Mode)"

    cd frontend/app

    print_info "Starting React development server..."
    print_info "Frontend will be available at: ${GREEN}http://localhost:3000${NC}"

    npm run dev &
    FRONTEND_PID=$!

    cd ../..

    # Save PID for cleanup
    echo $FRONTEND_PID > .frontend.pid

    print_success "Frontend started (PID: $FRONTEND_PID)"
}

# Start both backend and frontend
start_all() {
    print_header "Starting Full Stack (Development Mode)"

    # Check if frontend should be started
    read -p "Start frontend development server? (Y/n): " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        # Start frontend in background
        start_frontend &

        # Wait a bit for frontend to start
        sleep 2
    fi

    # Start backend in foreground (with reload)
    start_backend
}

# Cleanup on exit
cleanup() {
    echo ""
    print_info "Shutting down development servers..."

    # Kill frontend if running
    if [ -f ".frontend.pid" ]; then
        FRONTEND_PID=$(cat .frontend.pid)
        if ps -p $FRONTEND_PID > /dev/null 2>&1; then
            kill $FRONTEND_PID
            print_success "Frontend stopped"
        fi
        rm .frontend.pid
    fi

    print_success "Development servers stopped"
    exit 0
}

# Trap Ctrl+C
trap cleanup SIGINT SIGTERM

# Show development info
show_dev_info() {
    print_header "RAG Chatbot - Development Mode"

    echo ""
    echo "Development Configuration:"
    echo "  - Hot-reload: ${GREEN}Enabled${NC}"
    echo "  - Debug mode: ${GREEN}Enabled${NC}"
    echo "  - Auto-restart: ${GREEN}Enabled${NC}"
    echo ""
    echo "Features enabled (check .env):"

    # Check feature flags
    if grep -q "^USE_LANGCHAIN_CHUNKING=true" .env; then
        echo "  - Semantic Chunking: ${GREEN}✓ Enabled${NC}"
    else
        echo "  - Semantic Chunking: ${YELLOW}✗ Disabled${NC}"
    fi

    if grep -q "^OCR_ENABLED=true" .env; then
        echo "  - OCR (Tesseract): ${GREEN}✓ Enabled${NC}"
    else
        echo "  - OCR (Tesseract): ${YELLOW}✗ Disabled${NC}"
    fi

    if grep -q "^USE_FAISS=true" .env; then
        echo "  - FAISS Acceleration: ${GREEN}✓ Enabled${NC}"
    else
        echo "  - FAISS Acceleration: ${YELLOW}✗ Disabled${NC}"
    fi

    if grep -q "^MULTI_QUERY_ENABLED=true" .env; then
        echo "  - Multi-Query Retrieval: ${GREEN}✓ Enabled${NC}"
    else
        echo "  - Multi-Query Retrieval: ${YELLOW}✗ Disabled${NC}"
    fi

    echo ""
    print_info "Edit .env to enable/disable features"
    echo ""
}

# Main execution
main() {
    detect_os
    activate_venv
    check_env
    check_postgres
    show_dev_info

    # Parse arguments
    case "${1:-all}" in
        backend)
            start_backend
            ;;
        frontend)
            start_frontend
            wait
            ;;
        all)
            start_all
            ;;
        *)
            echo "Usage: $0 {backend|frontend|all}"
            echo "  backend  - Start only the backend server"
            echo "  frontend - Start only the frontend server"
            echo "  all      - Start both servers (default)"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
