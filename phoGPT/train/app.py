"""
FastAPI application for training management.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from routers import train_router
from config.db_config import get_db_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="PhoGPT Training API",
    description="API for managing PhoGPT model training runs",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(train_router.router)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting PhoGPT Training API...")

    # Test database connection
    try:
        db_config = get_db_config()
        if db_config.test_connection():
            logger.info("✓ Database connection successful")
        else:
            logger.warning("⚠ Database connection failed - some features may not work")
    except Exception as e:
        logger.error(f"✗ Database initialization error: {str(e)}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down PhoGPT Training API...")
    from config.db_config import close_db_config
    close_db_config()


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "PhoGPT Training API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        db_config = get_db_config()
        db_healthy = db_config.test_connection()

        return {
            "status": "healthy" if db_healthy else "degraded",
            "database": "connected" if db_healthy else "disconnected",
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
