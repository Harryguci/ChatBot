#!/bin/bash

# ===================================================================
# RAG Chatbot - Project Setup Script
# ===================================================================
# This script sets up the project environment for the first time
# ===================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check if running on Windows (Git Bash/WSL)
check_os() {
    print_info "Detecting operating system..."

    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        OS_TYPE="windows"
        print_warning "Running on Windows (Git Bash)"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS_TYPE="linux"
        print_success "Running on Linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS_TYPE="mac"
        print_success "Running on macOS"
    else
        OS_TYPE="unknown"
        print_warning "Unknown OS: $OSTYPE"
    fi
}``

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"

    local all_good=true

    # Check Python
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        print_success "Python 3 found: $PYTHON_VERSION"
    elif command -v python &> /dev/null; then
        PYTHON_VERSION=$(python --version | cut -d' ' -f2)
        print_success "Python found: $PYTHON_VERSION"
    else
        print_error "Python not found! Please install Python 3.10 or higher"
        all_good=false
    fi

    # Check Node.js
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        print_success "Node.js found: $NODE_VERSION"
    else
        print_warning "Node.js not found (optional for frontend development)"
    fi

    # Check Docker
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | cut -d',' -f1)
        print_success "Docker found: $DOCKER_VERSION"
    else
        print_warning "Docker not found (optional for containerized deployment)"
    fi

    # Check Git
    if command -v git &> /dev/null; then
        GIT_VERSION=$(git --version | cut -d' ' -f3)
        print_success "Git found: $GIT_VERSION"
    else
        print_warning "Git not found"
    fi

    if [ "$all_good" = false ]; then
        print_error "Please install missing prerequisites and run setup again"
        exit 1
    fi
}

# Create virtual environment
setup_venv() {
    print_header "Setting Up Python Virtual Environment"

    if [ -d ".venv" ]; then
        print_warning "Virtual environment already exists"
        read -p "Do you want to recreate it? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "Removing old virtual environment..."
            rm -rf .venv
        else
            print_info "Keeping existing virtual environment"
            return
        fi
    fi

    print_info "Creating virtual environment..."

    if command -v python3 &> /dev/null; then
        python3 -m venv .venv
    else
        python -m venv .venv
    fi

    print_success "Virtual environment created"
}

# Activate virtual environment
activate_venv() {
    print_info "Activating virtual environment..."

    if [ "$OS_TYPE" = "windows" ]; then
        source .venv/Scripts/activate
    else
        source .venv/bin/activate
    fi

    print_success "Virtual environment activated"
}

# Install Python dependencies
install_python_deps() {
    print_header "Installing Python Dependencies"

    print_info "Upgrading pip..."
    pip install --upgrade pip

    print_info "Installing requirements..."
    pip install -r requirements.txt

    print_success "Python dependencies installed"
}

# Setup environment file
setup_env() {
    print_header "Setting Up Environment Variables"

    if [ -f ".env" ]; then
        print_warning ".env file already exists"
        read -p "Do you want to overwrite it? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Keeping existing .env file"
            return
        fi
    fi

    print_info "Copying .env.example to .env..."
    cp .env.example .env

    print_success ".env file created"
    print_warning "IMPORTANT: Please edit .env and add your API keys!"

    echo ""
    echo "Required configuration:"
    echo "  1. GOOGLE_API_KEY - Get from: https://makersuite.google.com/app/apikey"
    echo "  2. JWT_SECRET_KEY - Generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
    echo "  3. Database credentials (if using external database)"
    echo ""
}

# Setup PostgreSQL with Docker
setup_postgres() {
    print_header "Setting Up PostgreSQL Database"

    if ! command -v docker &> /dev/null; then
        print_warning "Docker not found. Skipping PostgreSQL setup"
        print_info "You'll need to install PostgreSQL manually or use Docker later"
        return
    fi

    read -p "Do you want to start PostgreSQL with Docker? (Y/n): " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        print_info "Starting PostgreSQL container..."

        cd docker
        docker-compose up -d postgres
        cd ..

        print_success "PostgreSQL container started"
        print_info "Waiting for PostgreSQL to be ready..."
        sleep 5

        print_success "PostgreSQL is ready at localhost:5432"
    else
        print_info "Skipping PostgreSQL setup"
        print_warning "Make sure you have PostgreSQL installed and running"
    fi
}

# Setup Tesseract OCR
setup_tesseract() {
    print_header "Checking Tesseract OCR"

    if command -v tesseract &> /dev/null; then
        TESS_VERSION=$(tesseract --version | head -n1)
        print_success "Tesseract found: $TESS_VERSION"

        # Check for Vietnamese language
        if tesseract --list-langs | grep -q "vie"; then
            print_success "Vietnamese language pack installed"
        else
            print_warning "Vietnamese language pack not found"
            print_info "Install with: sudo apt-get install tesseract-ocr-vie (Linux)"
        fi
    else
        print_warning "Tesseract OCR not found"

        if [ "$OS_TYPE" = "linux" ]; then
            print_info "Install with: sudo apt-get install tesseract-ocr tesseract-ocr-eng tesseract-ocr-vie"
        elif [ "$OS_TYPE" = "mac" ]; then
            print_info "Install with: brew install tesseract tesseract-lang"
        elif [ "$OS_TYPE" = "windows" ]; then
            print_info "Download from: https://github.com/UB-Mannheim/tesseract/wiki"
        fi
    fi
}

# Initialize database
init_database() {
    print_header "Initializing Database"

    read -p "Do you want to run database migrations? (Y/n): " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        print_info "Running Alembic migrations..."

        # Check if alembic is configured
        if [ -f "alembic.ini" ]; then
            alembic upgrade head
            print_success "Database migrations completed"
        else
            print_warning "Alembic not configured. Skipping migrations"
            print_info "Database tables will be created on first run"
        fi
    fi
}

# Create necessary directories
create_directories() {
    print_header "Creating Project Directories"

    print_info "Creating data directories..."
    mkdir -p data/faiss
    mkdir -p data/uploads
    mkdir -p logs

    print_success "Directories created"
}

# Setup frontend (optional)
setup_frontend() {
    print_header "Frontend Setup (Optional)"

    if [ ! -d "frontend/app" ]; then
        print_info "Frontend directory not found. Skipping"
        return
    fi

    if ! command -v node &> /dev/null; then
        print_warning "Node.js not found. Skipping frontend setup"
        return
    fi

    read -p "Do you want to setup the frontend? (Y/n): " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        print_info "Installing frontend dependencies..."

        cd frontend/app

        if [ -f "package.json" ]; then
            npm install
            print_success "Frontend dependencies installed"
        fi

        cd ../..
    fi
}

# Print final instructions
print_final_instructions() {
    print_header "Setup Complete!"

    echo ""
    echo -e "${GREEN}✓ Project setup completed successfully!${NC}"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Configure your environment:"
    echo "   ${YELLOW}nano .env${NC}  # or your favorite editor"
    echo ""
    echo "2. Start development server:"
    echo "   ${YELLOW}./dev.sh${NC}"
    echo ""
    echo "3. Or start production server:"
    echo "   ${YELLOW}./prod.sh${NC}"
    echo ""
    echo "4. Access the application:"
    echo "   API: ${BLUE}http://localhost:8000${NC}"
    echo "   Frontend: ${BLUE}http://localhost:3000${NC}"
    echo "   API Docs: ${BLUE}http://localhost:8000/docs${NC}"
    echo ""
    echo -e "${YELLOW}Important:${NC}"
    echo "  - Edit ${YELLOW}.env${NC} and add your GOOGLE_API_KEY"
    echo "  - Ensure PostgreSQL is running (port 5432)"
    echo "  - For OCR support, install Tesseract"
    echo ""
    echo "Documentation:"
    echo "  - User Guide: ${BLUE}docs/RAG_ENHANCEMENTS_README.md${NC}"
    echo "  - API Docs: ${BLUE}docs/API_DOCUMENTATION.md${NC}"
    echo "  - Enhancement Details: ${BLUE}docs/IMPLEMENTATION_SUMMARY.md${NC}"
    echo ""
}

# Main execution
main() {
    print_header "RAG Chatbot - Project Setup"

    print_info "This script will set up your development environment"
    echo ""

    check_os
    check_prerequisites

    setup_venv
    activate_venv
    install_python_deps

    setup_env
    create_directories
    setup_postgres
    setup_tesseract
    init_database
    setup_frontend

    print_final_instructions
}

# Run main function
main
