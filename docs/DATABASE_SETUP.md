# Database Setup Guide

This guide explains how to set up and use the PostgreSQL database connection for the chatbot application.

## Prerequisites

- PostgreSQL 12+ installed locally or via Docker
- Python dependencies installed (`pip install -r requirements.txt`)

## Environment Configuration

Create a `.env` file in the project root with the following variables:

```env
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=chatbot_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
DB_ECHO=false

# Google API Configuration
GOOGLE_API_KEY=your_google_api_key_here

# Application Configuration
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
```

## Database Setup

### Option 1: Using Docker Compose (Recommended)

1. Navigate to the `docker` directory:
   ```bash
   cd docker
   ```

2. Start PostgreSQL service:
   ```bash
   docker-compose up postgres -d
   ```

3. The database will be automatically created with the configuration from your `.env` file.

### Option 2: Manual Setup

1. Install PostgreSQL locally
2. Create a database:
   ```sql
   CREATE DATABASE chatbot_db;
   CREATE USER postgres WITH PASSWORD 'postgres';
   GRANT ALL PRIVILEGES ON DATABASE chatbot_db TO postgres;
   ```

## Database Initialization

### Using the Database Initializer

```python
from src.config.db.db_init import initialize_database_from_env

# Initialize database (creates database if it doesn't exist)
success = initialize_database_from_env()
if success:
    print("Database initialized successfully")
else:
    print("Database initialization failed")
```

### Using Command Line

```bash
# Create database
python src/config/db/db_init.py create

# Setup database (create + test connection)
python src/config/db/db_init.py setup

# Test connection
python src/config/db/db_init.py test

# Drop database (use with caution!)
python src/config/db/db_init.py drop
```

## Using the Database Connection

### Basic Usage

```python
from src.config.db import get_database_connection

# Get database connection
db = get_database_connection()

# Test connection
if db.test_connection():
    print("Database connected successfully")

# Use session context manager
with db.get_session() as session:
    result = session.execute(text("SELECT version()"))
    version = result.scalar()
    print(f"PostgreSQL version: {version}")
```

### Using Database Services

```python
from src.config.db.services import (
    user_service, document_service, conversation_service
)

# Create a user
user = user_service.create_user(
    username="john_doe",
    email="john@example.com",
    full_name="John Doe"
)

# Create a document
document = document_service.create_document(
    filename="document.pdf",
    original_filename="My Document.pdf",
    file_type="PDF",
    content_hash="abc123...",
    file_size=1024000
)

# Create a conversation
conversation = conversation_service.create_conversation(
    session_id="session_123",
    user_id=user.id,
    title="Chat about documents"
)
```

### Using Database Models

```python
from src.config.db.models import Base
from src.config.db import get_database_connection

# Create all tables
db = get_database_connection()
db.create_tables(Base)
```

## Database Models

The application includes the following database models:

- **User**: User accounts and profiles
- **Document**: Processed documents (PDF, images)
- **DocumentChunk**: Text chunks with embeddings
- **Conversation**: Chat sessions
- **Message**: Individual chat messages
- **ChatbotSession**: Current session state
- **EmbeddingCache**: Cached embeddings
- **SystemLog**: Application logs

## Connection Pooling

The database connection uses SQLAlchemy's connection pooling:

- **Pool Size**: Number of persistent connections (default: 10)
- **Max Overflow**: Additional connections when pool is full (default: 20)
- **Pool Timeout**: Seconds to wait for connection (default: 30)
- **Pool Recycle**: Seconds before connection is recycled (default: 3600)

## Troubleshooting

### Connection Issues

1. Check PostgreSQL is running:
   ```bash
   # Docker
   docker ps | grep postgres
   
   # Local
   sudo systemctl status postgresql
   ```

2. Verify database credentials in `.env` file

3. Test connection:
   ```python
   from src.config.db.db_connection import test_database_setup
   test_database_setup()
   ```

### Permission Issues

```sql
-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE chatbot_db TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
```

### Performance Issues

- Increase pool size for high-traffic applications
- Monitor connection usage with PostgreSQL logs
- Use connection pooling effectively
- Consider read replicas for read-heavy workloads

## Development vs Production

### Development
- Use local PostgreSQL or Docker
- Enable SQL query logging (`DB_ECHO=true`)
- Use smaller pool sizes
- Enable debug logging

### Production
- Use managed PostgreSQL service (AWS RDS, Google Cloud SQL, etc.)
- Disable SQL query logging (`DB_ECHO=false`)
- Use larger pool sizes based on load
- Enable connection monitoring
- Use SSL connections
- Implement backup strategies

## Security Considerations

1. **Environment Variables**: Never commit `.env` files to version control
2. **Database Credentials**: Use strong passwords
3. **Network Security**: Restrict database access to application servers
4. **SSL**: Use SSL connections in production
5. **Backups**: Implement regular database backups
6. **Monitoring**: Monitor database performance and access logs
