"""
Unit tests for the Chatbot API endpoints.
"""

import pytest
import os
import tempfile
from unittest.mock import patch, Mock, MagicMock
from fastapi.testclient import TestClient
from fastapi import status
import json

from src.routers.chatbot import router, get_chatbot, chatbot_instance


class TestChatbotAPI:
    """Test class for chatbot API endpoints."""
    
    def test_health_check_healthy(self, test_client):
        """Test health check endpoint when service is healthy."""
        with patch('src.routers.chatbot.chatbot_instance', None):
            response = test_client.get("/api/chatbot/health")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "chatbot-api"
    
    def test_health_check_no_api_key(self, test_client):
        """Test health check endpoint when API key is not configured."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('src.routers.chatbot.chatbot_instance', None):
                response = test_client.get("/api/chatbot/health")
                assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
                data = response.json()
                assert data["status"] == "unhealthy"
                assert "Google API key not configured" in data["reason"]
    
    @patch('src.routers.chatbot.PDFChatbot')
    def test_upload_pdf_success(self, mock_pdf_chatbot_class, test_client, mock_pdf_file):
        """Test successful PDF upload and processing."""
        # Setup mock
        mock_chatbot = Mock()
        mock_chatbot.process_pdf.return_value = (
            "Xử lý thành công 'test.pdf'!\n- Số chunks mới: 5\n- Tổng số chunks trong bộ nhớ: 5",
            "**Các tài liệu trong bộ nhớ:**\n1. test.pdf"
        )
        mock_pdf_chatbot_class.return_value = mock_chatbot
        
        # Override the dependency
        def mock_get_chatbot():
            return mock_chatbot
        
        test_client.app.dependency_overrides[get_chatbot] = mock_get_chatbot
        
        try:
            with open(mock_pdf_file, 'rb') as f:
                files = {'file': ('test.pdf', f, 'application/pdf')}
                response = test_client.post("/api/chatbot/upload-pdf", files=files)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "status" in data
            assert "processed_files" in data
            assert "total_chunks" in data
            assert data["total_chunks"] == 5
            assert "test.pdf" in data["status"]
            
            # Verify the mock was called
            mock_chatbot.process_pdf.assert_called_once()
            
        finally:
            # Clean up dependency override
            test_client.app.dependency_overrides.clear()
    
    def test_upload_pdf_invalid_file_type(self, test_client, mock_chatbot):
        """Test PDF upload with invalid file type."""
        def mock_get_chatbot():
            return mock_chatbot
        
        test_client.app.dependency_overrides[get_chatbot] = mock_get_chatbot
        
        try:
            # Create a temporary text file instead of PDF
            with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp_file:
                tmp_file.write(b'This is not a PDF file')
                tmp_file_path = tmp_file.name
            
            try:
                with open(tmp_file_path, 'rb') as f:
                    files = {'file': ('test.txt', f, 'text/plain')}
                    response = test_client.post("/api/chatbot/upload-pdf", files=files)
                
                assert response.status_code == status.HTTP_400_BAD_REQUEST
                data = response.json()
                assert "Only PDF files are supported" in data["detail"]
                
            finally:
                os.unlink(tmp_file_path)
                
        finally:
            test_client.app.dependency_overrides.clear()
    
    def test_upload_pdf_processing_error(self, test_client, mock_chatbot):
        """Test PDF upload when processing fails."""
        # Setup mock to raise an exception
        mock_chatbot.process_pdf.side_effect = Exception("Processing failed")
        
        def mock_get_chatbot():
            return mock_chatbot
        
        test_client.app.dependency_overrides[get_chatbot] = mock_get_chatbot
        
        try:
            # Create a temporary PDF file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                tmp_file.write(b'%PDF-1.4\n%Test content\n')
                tmp_file_path = tmp_file.name
            
            try:
                with open(tmp_file_path, 'rb') as f:
                    files = {'file': ('test.pdf', f, 'application/pdf')}
                    response = test_client.post("/api/chatbot/upload-pdf", files=files)
                
                assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
                data = response.json()
                assert "Error processing PDF" in data["detail"]
                
            finally:
                os.unlink(tmp_file_path)
                
        finally:
            test_client.app.dependency_overrides.clear()
    
    def test_chat_success(self, test_client, mock_chatbot, sample_chat_request):
        """Test successful chat interaction."""
        # Setup mock response
        mock_chatbot.generate_answer.return_value = (
            "",
            [("What is this document about?", "This document is about test content.\n\n---\n*Độ tin cậy của nguồn chính: 85%* (Cao)")]
        )
        
        def mock_get_chatbot():
            return mock_chatbot
        
        test_client.app.dependency_overrides[get_chatbot] = mock_get_chatbot
        
        try:
            response = test_client.post("/api/chatbot/chat", json=sample_chat_request)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "answer" in data
            assert "chat_history" in data
            assert "confidence" in data
            assert data["confidence"] == 0.85
            assert "test content" in data["answer"]
            
            # Verify the mock was called with correct parameters
            mock_chatbot.generate_answer.assert_called_once_with(
                sample_chat_request["query"], 
                sample_chat_request["chat_history"]
            )
            
        finally:
            test_client.app.dependency_overrides.clear()
    
    def test_chat_empty_query(self, test_client, mock_chatbot):
        """Test chat with empty query."""
        def mock_get_chatbot():
            return mock_chatbot
        
        test_client.app.dependency_overrides[get_chatbot] = mock_get_chatbot
        
        try:
            response = test_client.post("/api/chatbot/chat", json={"query": "", "chat_history": []})
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            data = response.json()
            assert "Query cannot be empty" in data["detail"]
            
        finally:
            test_client.app.dependency_overrides.clear()
    
    def test_chat_whitespace_only_query(self, test_client, mock_chatbot):
        """Test chat with whitespace-only query."""
        def mock_get_chatbot():
            return mock_chatbot
        
        test_client.app.dependency_overrides[get_chatbot] = mock_get_chatbot
        
        try:
            response = test_client.post("/api/chatbot/chat", json={"query": "   ", "chat_history": []})
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            data = response.json()
            assert "Query cannot be empty" in data["detail"]
            
        finally:
            test_client.app.dependency_overrides.clear()
    
    def test_chat_generation_error(self, test_client, mock_chatbot, sample_chat_request):
        """Test chat when answer generation fails."""
        # Setup mock to raise an exception
        mock_chatbot.generate_answer.side_effect = Exception("Generation failed")
        
        def mock_get_chatbot():
            return mock_chatbot
        
        test_client.app.dependency_overrides[get_chatbot] = mock_get_chatbot
        
        try:
            response = test_client.post("/api/chatbot/chat", json=sample_chat_request)
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            assert "Error generating answer" in data["detail"]
            
        finally:
            test_client.app.dependency_overrides.clear()
    
    def test_clear_memory_success(self, test_client, mock_chatbot):
        """Test successful memory clearing."""
        def mock_get_chatbot():
            return mock_chatbot
        
        test_client.app.dependency_overrides[get_chatbot] = mock_get_chatbot
        
        try:
            response = test_client.delete("/api/chatbot/memory")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["message"] == "Memory cleared successfully"
            assert data["status"] == "success"
            
            # Verify the mock was called
            mock_chatbot.clear_memory.assert_called_once()
            
        finally:
            test_client.app.dependency_overrides.clear()
    
    def test_clear_memory_error(self, test_client, mock_chatbot):
        """Test memory clearing when it fails."""
        # Setup mock to raise an exception
        mock_chatbot.clear_memory.side_effect = Exception("Clear failed")
        
        def mock_get_chatbot():
            return mock_chatbot
        
        test_client.app.dependency_overrides[get_chatbot] = mock_get_chatbot
        
        try:
            response = test_client.delete("/api/chatbot/memory")
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            assert "Error clearing memory" in data["detail"]
            
        finally:
            test_client.app.dependency_overrides.clear()
    
    def test_get_memory_status_success(self, test_client, mock_chatbot, sample_memory_status):
        """Test successful memory status retrieval."""
        # Setup mock attributes
        mock_chatbot.processed_files = {"test1.pdf", "test2.pdf"}
        mock_chatbot.documents = ["doc1", "doc2"] * 12 + ["doc25"]  # 25 documents
        mock_chatbot.document_metadata = ["meta1"] * 25  # 25 metadata entries
        
        def mock_get_chatbot():
            return mock_chatbot
        
        test_client.app.dependency_overrides[get_chatbot] = mock_get_chatbot
        
        try:
            response = test_client.get("/api/chatbot/memory/status")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "processed_files" in data
            assert "total_chunks" in data
            assert "total_documents" in data
            assert len(data["processed_files"]) == 2
            assert data["total_chunks"] == 25
            assert data["total_documents"] == 25
            assert "test1.pdf" in data["processed_files"]
            assert "test2.pdf" in data["processed_files"]
            
        finally:
            test_client.app.dependency_overrides.clear()
    
    def test_get_memory_status_error(self, test_client, mock_chatbot):
        """Test memory status retrieval when it fails."""
        # Setup mock to raise an exception when accessing attributes
        mock_chatbot.processed_files = Mock(side_effect=Exception("Access failed"))
        
        def mock_get_chatbot():
            return mock_chatbot
        
        test_client.app.dependency_overrides[get_chatbot] = mock_get_chatbot
        
        try:
            response = test_client.get("/api/chatbot/memory/status")
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            assert "Error getting memory status" in data["detail"]
            
        finally:
            test_client.app.dependency_overrides.clear()


class TestChatbotDependency:
    """Test the chatbot dependency function."""
    
    def test_get_chatbot_no_api_key(self):
        """Test get_chatbot when API key is not set."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(Exception) as exc_info:
                get_chatbot()
            assert "Google API key not found" in str(exc_info.value)
    
    @patch('src.routers.chatbot.PDFChatbot')
    def test_get_chatbot_success(self, mock_pdf_chatbot_class):
        """Test successful chatbot initialization."""
        mock_chatbot = Mock()
        mock_pdf_chatbot_class.return_value = mock_chatbot
        
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test_key"}):
            result = get_chatbot()
            assert result == mock_chatbot
            mock_pdf_chatbot_class.assert_called_once_with("test_key")
    
    @patch('src.routers.chatbot.PDFChatbot')
    def test_get_chatbot_initialization_error(self, mock_pdf_chatbot_class):
        """Test get_chatbot when initialization fails."""
        mock_pdf_chatbot_class.side_effect = Exception("Init failed")
        
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test_key"}):
            with pytest.raises(Exception) as exc_info:
                get_chatbot()
            assert "Failed to initialize chatbot" in str(exc_info.value)
    
    def test_get_chatbot_reuse_instance(self):
        """Test that get_chatbot reuses existing instance."""
        global chatbot_instance
        original_instance = chatbot_instance
        
        try:
            # Set up a mock instance
            mock_instance = Mock()
            chatbot_instance = mock_instance
            
            # Call get_chatbot - should return existing instance
            result = get_chatbot()
            assert result == mock_instance
            
        finally:
            chatbot_instance = original_instance
