#!/bin/bash

# ===================================================================
# RAG Chatbot - Production Mode Runner
# ===================================================================
# This script runs the project in production mode with Docker
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

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"

    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker not found!"
        print_info "Install from: https://docs.docker.com/get-docker/"
        exit 1
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose not found!"
        print_info "Install from: https://docs.docker.com/compose/install/"
        exit 1
    fi

    DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | cut -d',' -f1)
    COMPOSE_VERSION=$(docker-compose --version | cut -d' ' -f3 | cut -d',' -f1)

    print_success "Docker: $DOCKER_VERSION"
    print_success "Docker Compose: $COMPOSE_VERSION"
}

# Check .env file
check_env() {
    print_header "Checking Environment Configuration"

    if [ ! -f ".env" ]; then
        print_warning ".env file not found"
        print_info "Creating from .env.example..."
        cp .env.example .env
        print_error "Please edit .env and configure production settings!"
        exit 1
    fi

    # Check critical variables
    local missing_vars=()

    if grep -q "GOOGLE_API_KEY=your_google_api_key_here" .env; then
        missing_vars+=("GOOGLE_API_KEY")
    fi

    if grep -q "JWT_SECRET_KEY=change-this" .env; then
        missing_vars+=("JWT_SECRET_KEY")
    fi

    if [ ${#missing_vars[@]} -gt 0 ]; then
        print_error "Missing configuration: ${missing_vars[*]}"
        print_info "Please configure these variables in .env"
        exit 1
    fi

    print_success "Environment configuration valid"
}

# Build Docker images
build_images() {
    print_header "Building Docker Images"

    print_info "This may take several minutes on first run..."

    cd docker

    # Build with no cache option
    if [ "${1}" = "--no-cache" ]; then
        print_info "Building with --no-cache..."
        docker-compose build --no-cache
    else
        docker-compose build
    fi

    cd ..

    print_success "Docker images built successfully"
}

# Start services
start_services() {
    print_header "Starting Production Services"

    cd docker

    # Check what profile to use
    local PROFILE=""

    read -p "Include frontend container? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        PROFILE="--profile dev"
        print_info "Starting with frontend (dev profile)..."
    fi

    # Start services
    print_info "Starting containers..."
    docker-compose $PROFILE up -d

    cd ..

    # Wait for services to be healthy
    print_info "Waiting for services to be ready..."
    sleep 5

    print_success "Services started"
}

# Stop services
stop_services() {
    print_header "Stopping Production Services"

    cd docker
    docker-compose down
    cd ..

    print_success "Services stopped"
}

# Show logs
show_logs() {
    print_header "Service Logs"

    cd docker

    # Follow logs
    print_info "Showing logs (Ctrl+C to exit)..."
    docker-compose logs -f --tail=100

    cd ..
}

# Show status
show_status() {
    print_header "Service Status"

    cd docker
    docker-compose ps
    cd ..

    echo ""
    print_info "Access points:"
    echo "  API: ${GREEN}http://localhost:8000${NC}"
    echo "  API Docs: ${GREEN}http://localhost:8000/docs${NC}"
    echo "  PostgreSQL: ${GREEN}localhost:5432${NC}"

    # Check if frontend is running
    if docker ps | grep -q "chatbot-frontend"; then
        echo "  Frontend: ${GREEN}http://localhost:3000${NC}"
    fi

    echo ""
}

# Restart services
restart_services() {
    print_header "Restarting Services"

    stop_services
    sleep 2
    start_services
    sleep 2
    show_status
}

# Run database migrations
run_migrations() {
    print_header "Running Database Migrations"

    cd docker

    print_info "Executing Alembic migrations..."

    # Run migrations in backend container
    docker-compose exec backend alembic upgrade head

    cd ..

    print_success "Migrations completed"
}

# Backup database
backup_database() {
    print_header "Backing Up Database"

    local BACKUP_DIR="backups"
    local TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    local BACKUP_FILE="${BACKUP_DIR}/chatbot_db_${TIMESTAMP}.sql"

    mkdir -p "$BACKUP_DIR"

    print_info "Creating backup: $BACKUP_FILE"

    cd docker

    # Get database credentials from .env or use defaults
    DB_NAME=$(grep "^DB_NAME=" ../.env | cut -d'=' -f2 || echo "chatbot_db")
    DB_USER=$(grep "^DB_USER=" ../.env | cut -d'=' -f2 || echo "postgres")

    # Create backup
    docker-compose exec -T postgres pg_dump -U "$DB_USER" "$DB_NAME" > "../$BACKUP_FILE"

    cd ..

    if [ -f "$BACKUP_FILE" ]; then
        BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        print_success "Backup created: $BACKUP_FILE ($BACKUP_SIZE)"
    else
        print_error "Backup failed"
        exit 1
    fi
}

# Restore database
restore_database() {
    print_header "Restoring Database"

    local BACKUP_DIR="backups"

    if [ ! -d "$BACKUP_DIR" ]; then
        print_error "Backup directory not found"
        exit 1
    fi

    # List available backups
    print_info "Available backups:"
    ls -lh "$BACKUP_DIR"/*.sql 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'

    echo ""
    read -p "Enter backup filename to restore: " BACKUP_FILE

    if [ ! -f "$BACKUP_DIR/$BACKUP_FILE" ]; then
        print_error "Backup file not found: $BACKUP_DIR/$BACKUP_FILE"
        exit 1
    fi

    print_warning "This will overwrite the current database!"
    read -p "Are you sure? (yes/NO): " CONFIRM

    if [ "$CONFIRM" != "yes" ]; then
        print_info "Restore cancelled"
        exit 0
    fi

    cd docker

    # Get database credentials
    DB_NAME=$(grep "^DB_NAME=" ../.env | cut -d'=' -f2 || echo "chatbot_db")
    DB_USER=$(grep "^DB_USER=" ../.env | cut -d'=' -f2 || echo "postgres")

    print_info "Restoring from $BACKUP_FILE..."

    # Restore backup
    cat "../$BACKUP_DIR/$BACKUP_FILE" | docker-compose exec -T postgres psql -U "$DB_USER" "$DB_NAME"

    cd ..

    print_success "Database restored"
}

# Show production info
show_production_info() {
    print_header "Production Configuration"

    echo ""
    echo "Services:"
    echo "  - Backend (FastAPI)"
    echo "  - PostgreSQL with pgvector"
    echo "  - Frontend (optional)"
    echo ""
    echo "Features (from .env):"

    # Show feature status
    if grep -q "^USE_LANGCHAIN_CHUNKING=true" .env 2>/dev/null; then
        echo "  - Semantic Chunking: ${GREEN}✓ Enabled${NC}"
    else
        echo "  - Semantic Chunking: ${YELLOW}✗ Disabled${NC}"
    fi

    if grep -q "^OCR_ENABLED=true" .env 2>/dev/null; then
        echo "  - OCR (Tesseract): ${GREEN}✓ Enabled${NC}"
    else
        echo "  - OCR (Tesseract): ${YELLOW}✗ Disabled${NC}"
    fi

    if grep -q "^USE_FAISS=true" .env 2>/dev/null; then
        echo "  - FAISS Acceleration: ${GREEN}✓ Enabled${NC}"
    else
        echo "  - FAISS Acceleration: ${YELLOW}✗ Disabled${NC}"
    fi

    if grep -q "^MULTI_QUERY_ENABLED=true" .env 2>/dev/null; then
        echo "  - Multi-Query: ${GREEN}✓ Enabled${NC}"
    else
        echo "  - Multi-Query: ${YELLOW}✗ Disabled${NC}"
    fi

    echo ""
    echo "Production Optimizations:"
    echo "  - Gunicorn workers: 4"
    echo "  - DB connection pool: 50 (max 100)"
    echo "  - Auto-restart on failure"
    echo "  - Health checks enabled"
    echo ""
}

# Main execution
main() {
    case "${1:-start}" in
        start)
            check_prerequisites
            check_env
            build_images
            start_services
            show_status
            ;;

        stop)
            stop_services
            ;;

        restart)
            restart_services
            ;;

        rebuild)
            check_prerequisites
            check_env
            build_images --no-cache
            restart_services
            ;;

        logs)
            show_logs
            ;;

        status)
            show_status
            ;;

        migrate)
            run_migrations
            ;;

        backup)
            backup_database
            ;;

        restore)
            restore_database
            ;;

        info)
            show_production_info
            ;;

        shell)
            print_header "Opening Shell in Backend Container"
            cd docker
            docker-compose exec backend /bin/bash
            cd ..
            ;;

        *)
            echo "Usage: $0 {start|stop|restart|rebuild|logs|status|migrate|backup|restore|info|shell}"
            echo ""
            echo "Commands:"
            echo "  start    - Build and start all services (default)"
            echo "  stop     - Stop all services"
            echo "  restart  - Restart all services"
            echo "  rebuild  - Rebuild images and restart (use after code changes)"
            echo "  logs     - Show service logs"
            echo "  status   - Show service status and access points"
            echo "  migrate  - Run database migrations"
            echo "  backup   - Create database backup"
            echo "  restore  - Restore database from backup"
            echo "  info     - Show production configuration"
            echo "  shell    - Open shell in backend container"
            echo ""
            echo "Examples:"
            echo "  $0 start          # Start production environment"
            echo "  $0 logs           # View logs"
            echo "  $0 rebuild        # Rebuild after code changes"
            echo "  $0 backup         # Create database backup"
            echo ""
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
