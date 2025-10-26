"""
Example integration of database connection into the main FastAPI application.
"""

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

from src.config.db import get_database_connection, initialize_database
from src.config.db.services import (
    user_service, document_service, conversation_service,
    system_log_service
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for database initialization."""
    # Startup
    try:
        # Initialize database connection
        db = initialize_database()
        
        # Test connection
        if db.test_connection():
            print("✓ Database connection established")
            system_log_service.log_event(
                level="INFO",
                logger_name="app.startup",
                message="Database connection established successfully"
            )
        else:
            print("✗ Database connection failed")
            system_log_service.log_event(
                level="ERROR", 
                logger_name="app.startup",
                message="Database connection failed"
            )
            
    except Exception as e:
        print(f"✗ Database initialization failed: {str(e)}")
        system_log_service.log_event(
            level="ERROR",
            logger_name="app.startup", 
            message=f"Database initialization failed: {str(e)}"
        )
    
    yield
    
    # Shutdown
    try:
        from src.config.db import close_database
        close_database()
        print("✓ Database connection closed")
    except Exception as e:
        print(f"✗ Error closing database: {str(e)}")


# Create FastAPI app with lifespan
app = FastAPI(
    title="Chatbot API",
    description="AI Chatbot with PostgreSQL integration",
    lifespan=lifespan
)


def get_db_session():
    """FastAPI dependency for database sessions."""
    db = get_database_connection()
    return db.get_session()


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    try:
        db = get_database_connection()
        if db.test_connection():
            return {"status": "healthy", "database": "connected"}
        else:
            return {"status": "unhealthy", "database": "disconnected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.get("/api/users")
async def get_users(db: Session = Depends(get_db_session)):
    """Get all users."""
    with db:
        users = user_service.get_all_users()
        return {"users": [{"id": u.id, "username": u.username} for u in users]}


@app.post("/api/users")
async def create_user(username: str, email: str = None, db: Session = Depends(get_db_session)):
    """Create a new user."""
    with db:
        try:
            user = user_service.create_user(username=username, email=email)
            return {"user": {"id": user.id, "username": user.username}}
        except Exception as e:
            return {"error": str(e)}


@app.get("/api/documents")
async def get_documents(db: Session = Depends(get_db_session)):
    """Get all documents."""
    with db:
        documents = document_service.get_all_documents()
        return {"documents": [{"id": d.id, "filename": d.filename} for d in documents]}


@app.get("/api/conversations/{session_id}")
async def get_conversation(session_id: str, db: Session = Depends(get_db_session)):
    """Get conversation by session ID."""
    with db:
        conversation = conversation_service.get_conversation_by_session_id(session_id)
        if conversation:
            return {"conversation": {"id": conversation.id, "session_id": conversation.session_id}}
        else:
            return {"error": "Conversation not found"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

