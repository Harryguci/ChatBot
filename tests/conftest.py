"""
Pytest configuration and fixtures for chatbot API tests.
"""

import pytest
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.main import app
from src.routers.chatbot import get_chatbot, chatbot_instance
from src.chatbot_memory import PDFChatbot

@pytest.fixture(scope="session")
def test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)

@pytest.fixture
def mock_chatbot():
    """Create a mock PDFChatbot instance."""
    mock_chatbot = Mock(spec=PDFChatbot)
    
    # Mock the attributes
    mock_chatbot.documents = []
    mock_chatbot.embeddings = None
    mock_chatbot.document_metadata = []
    mock_chatbot.processed_files = set()
    
    # Mock the methods
    mock_chatbot.process_pdf.return_value = (
        "Xử lý thành công 'test.pdf'!\n- Số chunks mới: 5\n- Tổng số chunks trong bộ nhớ: 5",
        "**Các tài liệu trong bộ nhớ:**\n1. test.pdf"
    )
    
    mock_chatbot.generate_answer.return_value = (
        "",
        [("Test question", "Test answer with confidence info")]
    )
    
    mock_chatbot.clear_memory.return_value = (
        [],
        "",
        "Sẵn sàng xử lý file mới...",
        "Chưa có tài liệu nào được xử lý."
    )
    
    return mock_chatbot

@pytest.fixture
def mock_pdf_file():
    """Create a temporary PDF file for testing."""
    # Create a temporary file that looks like a PDF
    temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
    temp_file.write(b'%PDF-1.4\n%Test PDF content\n')
    temp_file.close()
    
    yield temp_file.name
    
    # Cleanup
    if os.path.exists(temp_file.name):
        os.unlink(temp_file.name)

@pytest.fixture
def sample_chat_request():
    """Sample chat request data."""
    return {
        "query": "What is this document about?",
        "chat_history": []
    }

@pytest.fixture
def sample_chat_response():
    """Sample chat response data."""
    return {
        "answer": "This document is about test content.\n\n---\n*Độ tin cậy của nguồn chính: 85%* (Cao)",
        "chat_history": [("What is this document about?", "This document is about test content.")],
        "confidence": 0.85
    }

@pytest.fixture
def sample_memory_status():
    """Sample memory status data."""
    return {
        "processed_files": ["test1.pdf", "test2.pdf"],
        "total_chunks": 25,
        "total_documents": 25
    }

@pytest.fixture(autouse=True)
def mock_environment():
    """Mock environment variables for testing."""
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "test_api_key"}):
        yield

@pytest.fixture(autouse=True)
def reset_chatbot_instance():
    """Reset the global chatbot instance before each test."""
    global chatbot_instance
    original_instance = chatbot_instance
    chatbot_instance = None
    yield
    chatbot_instance = original_instance

@pytest.fixture
def mock_get_chatbot(mock_chatbot):
    """Mock the get_chatbot dependency."""
    def _mock_get_chatbot():
        return mock_chatbot
    
    return _mock_get_chatbot
