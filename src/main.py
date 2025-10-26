from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from dotenv import load_dotenv

from src.config.db.services import system_log_service

# Load environment variables from .env file
load_dotenv()

# Import chatbot router
from src.routers.chatbot import router as chatbot_router

# Import database connection
from src.config.db import get_database_connection, initialize_database

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

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include chatbot router
app.include_router(chatbot_router)

# Mount static files from the React app release folder
app.mount("/assets", StaticFiles(directory="frontend/release/assets"), name="assets")

# Serve static files like vite.svg
@app.get("/vite.svg")
async def serve_vite_svg():
    return FileResponse("frontend/release/vite.svg")

# API endpoints
@app.get("/api/")
def read_root():
    return {"message": "Hello World"}

@app.get("/api/health")
def health_check():
    """Health check endpoint with database status."""
    try:
        db = get_database_connection()
        db_status = "connected" if db.test_connection() else "disconnected"
        return {
            "status": "healthy",
            "database": db_status,
            "message": "Chatbot API is running"
        }
    except Exception as e:
        return {
            "status": "unhealthy", 
            "database": "error",
            "error": str(e)
        }

# SPA fallback - serve React app for all other routes
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    # Check if the file exists in the release folder
    file_path = f"frontend/release/{full_path}"
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    
    # For all other routes, serve the React app (SPA fallback)
    return FileResponse("frontend/release/index.html")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
