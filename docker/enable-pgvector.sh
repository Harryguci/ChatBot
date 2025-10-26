#!/bin/bash
# Script to enable pgvector extension on existing PostgreSQL database

# Database connection parameters
DB_USER=${DB_USER:-root}
DB_NAME=${DB_NAME:-CHATBOT_OCR_DB}
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}

echo "Enabling pgvector extension on database..."
echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo ""

# Try to create the extension
psql -U "$DB_USER" -d "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>&1

if [ $? -eq 0 ]; then
    echo "✓ pgvector extension enabled successfully!"
else
    echo "✗ Failed to enable pgvector extension"
    echo ""
    echo "If you're using Docker, you may need to:"
    echo "1. Restart the container with pgvector image"
    echo "2. Or install pgvector on your PostgreSQL server"
    echo ""
    echo "For Docker restart:"
    echo "  cd docker && docker-compose down && docker-compose up -d"
    echo ""
    echo "For manual installation on Linux:"
    echo "  sudo apt-get install postgresql-15-pgvector"
    echo "  sudo systemctl restart postgresql"
fi

