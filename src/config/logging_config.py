"""
Logging configuration for the chatbot application.
"""

import logging
import os
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Create logs directory if it doesn't exist
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Log file paths
APP_LOG_FILE = LOGS_DIR / "app.log"
ERROR_LOG_FILE = LOGS_DIR / "error.log"
AUTH_LOG_FILE = LOGS_DIR / "auth.log"

# Log format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(log_level: str = "INFO"):
    """
    Setup application logging with file and console handlers.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Convert log level string to logging level
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create formatters
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler (stdout)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # App log file handler (all logs)
    app_file_handler = RotatingFileHandler(
        APP_LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    app_file_handler.setLevel(level)
    app_file_handler.setFormatter(formatter)
    root_logger.addHandler(app_file_handler)
    
    # Error log file handler (errors only)
    error_file_handler = RotatingFileHandler(
        ERROR_LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(formatter)
    root_logger.addHandler(error_file_handler)
    
    # Log startup message
    logging.info("=" * 60)
    logging.info(f"Logging initialized - Level: {log_level}")
    logging.info(f"App log: {APP_LOG_FILE}")
    logging.info(f"Error log: {ERROR_LOG_FILE}")
    logging.info(f"Auth log: {AUTH_LOG_FILE}")
    logging.info("=" * 60)
    
    return root_logger


def get_auth_logger():
    """
    Get a dedicated logger for authentication events.
    """
    auth_logger = logging.getLogger("auth")
    
    # Check if handler already exists
    if not any(isinstance(h, RotatingFileHandler) and h.baseFilename == str(AUTH_LOG_FILE.absolute()) 
               for h in auth_logger.handlers):
        formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
        
        auth_file_handler = RotatingFileHandler(
            AUTH_LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        auth_file_handler.setLevel(logging.INFO)
        auth_file_handler.setFormatter(formatter)
        auth_logger.addHandler(auth_file_handler)
    
    return auth_logger


# Initialize logging when module is imported
def init_logging():
    """Initialize logging with environment-based configuration."""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    setup_logging(log_level)


if __name__ == "__main__":
    # Test logging setup
    init_logging()
    logging.debug("This is a debug message")
    logging.info("This is an info message")
    logging.warning("This is a warning message")
    logging.error("This is an error message")
    logging.critical("This is a critical message")
    
    auth_logger = get_auth_logger()
    auth_logger.info("This is an auth log message")
    
    print(f"\nLog files created in: {LOGS_DIR.absolute()}")

