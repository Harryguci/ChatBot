from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.status import HTTP_404_NOT_FOUND
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

# API endpoints - define these first
# @app.get("/api/")
# def read_root():
#     return {"message": "Hello World"}

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

# Include chatbot router AFTER other API endpoints
app.include_router(chatbot_router)

# Serve static assets from Vite build
# Keep assets under a dedicated mount
app.mount("/assets", StaticFiles(directory="frontend/release/assets"), name="assets")

# Serve specific top-level static files that the SPA expects
@app.get("/vite.svg", include_in_schema=False)
def vite_svg():
    path = os.path.join("frontend", "release", "vite.svg")
    if os.path.exists(path):
        return FileResponse(path)
    return JSONResponse(status_code=404, content={"detail": "Not found"})

# SPA fallback: return index.html for any non-API route
@app.get("/", include_in_schema=False)
@app.get("/{full_path:path}", include_in_schema=False)
def spa_fallback(full_path: str = ""):
    # Do not intercept API routes
    if full_path.startswith("api/") or full_path == "api":
        raise HTTPException(status_code=404)
    index_path = os.path.join("frontend", "release", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(status_code=404, content={"detail": "SPA index not found"})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
