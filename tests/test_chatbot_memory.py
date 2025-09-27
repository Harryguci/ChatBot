"""
Unit tests for the PDFChatbot class.
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
import numpy as np

# Import the chatbot class
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from chatbot_memory import PDFChatbot


class TestPDFChatbot:
    """Test class for PDFChatbot functionality."""
    
    @patch('chatbot_memory.genai')
    @patch('chatbot_memory.SentenceTransformer')
    def test_init_success(self, mock_sentence_transformer, mock_genai):
        """Test successful PDFChatbot initialization."""
        # Setup mocks
        mock_genai.configure = Mock()
        mock_model = Mock()
        mock_genai.GenerativeModel.return_value = mock_model
        mock_embedding_model = Mock()
        mock_sentence_transformer.return_value = mock_embedding_model
        
        # Initialize chatbot
        chatbot = PDFChatbot("test_api_key")
        
        # Verify initialization
        assert chatbot.google_api_key == "test_api_key"
        assert chatbot.llm == mock_model
        assert chatbot.embedding_model == mock_embedding_model
        assert chatbot.documents == []
        assert chatbot.embeddings is None
        assert chatbot.document_metadata == []
        assert chatbot.processed_files == set()
        
        # Verify mocks were called
        mock_genai.configure.assert_called_once_with(api_key="test_api_key")
        mock_genai.GenerativeModel.assert_called_once_with('gemini-1.5-flash')
        mock_sentence_transformer.assert_called_once_with('paraphrase-multilingual-MiniLM-L12-v2')
    
    @patch('chatbot_memory.genai')
    @patch('chatbot_memory.SentenceTransformer')
    def test_init_failure(self, mock_sentence_transformer, mock_genai):
        """Test PDFChatbot initialization failure."""
        mock_genai.configure.side_effect = Exception("API key invalid")
        
        with pytest.raises(Exception) as exc_info:
            PDFChatbot("invalid_key")
        assert "API key invalid" in str(exc_info.value)
    
    def test_clear_memory(self):
        """Test memory clearing functionality."""
        with patch('chatbot_memory.genai'), patch('chatbot_memory.SentenceTransformer'):
            chatbot = PDFChatbot("test_key")
            
            # Add some test data
            chatbot.documents = ["doc1", "doc2"]
            chatbot.embeddings = np.array([[1, 2], [3, 4]])
            chatbot.document_metadata = [{"id": 1}, {"id": 2}]
            chatbot.processed_files = {"file1.pdf", "file2.pdf"}
            
            # Clear memory
            result = chatbot.clear_memory()
            
            # Verify memory is cleared
            assert chatbot.documents == []
            assert chatbot.embeddings is None
            assert chatbot.document_metadata == []
            assert chatbot.processed_files == set()
            
            # Verify return value
            assert result == ([], "", "Sẵn sàng xử lý file mới...", "Chưa có tài liệu nào được xử lý.")
    
    @patch('builtins.open', create=True)
    @patch('chatbot_memory.PyPDF2.PdfReader')
    def test_extract_text_from_pdf_success(self, mock_pdf_reader, mock_open):
        """Test successful PDF text extraction."""
        # Setup mocks
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        mock_reader = Mock()
        mock_page1 = Mock()
        mock_page1.extract_text.return_value = "Page 1 content"
        mock_page2 = Mock()
        mock_page2.extract_text.return_value = "Page 2 content"
        mock_reader.pages = [mock_page1, mock_page2]
        mock_pdf_reader.return_value = mock_reader
        
        with patch('chatbot_memory.genai'), patch('chatbot_memory.SentenceTransformer'):
            chatbot = PDFChatbot("test_key")
            
            result = chatbot.extract_text_from_pdf("test.pdf")
            
            expected = "Page 1 content\nPage 2 content\n"
            assert result == expected
            mock_open.assert_called_once_with("test.pdf", 'rb')
    
    @patch('builtins.open', create=True)
    @patch('chatbot_memory.PyPDF2.PdfReader')
    def test_extract_text_from_pdf_failure(self, mock_pdf_reader, mock_open):
        """Test PDF text extraction failure."""
        mock_open.side_effect = Exception("File not found")
        
        with patch('chatbot_memory.genai'), patch('chatbot_memory.SentenceTransformer'):
            chatbot = PDFChatbot("test_key")
            
            with pytest.raises(Exception) as exc_info:
                chatbot.extract_text_from_pdf("nonexistent.pdf")
            assert "File not found" in str(exc_info.value)
    
    def test_clean_text(self):
        """Test text cleaning functionality."""
        with patch('chatbot_memory.genai'), patch('chatbot_memory.SentenceTransformer'):
            chatbot = PDFChatbot("test_key")
            
            dirty_text = "  Multiple    spaces\n\n\nAnd   newlines  "
            result = chatbot.clean_text(dirty_text)
            expected = "Multiple spaces\n\nAnd newlines"
            assert result == expected
    
    def test_powerful_chunking_strategy(self):
        """Test document chunking strategy."""
        with patch('chatbot_memory.genai'), patch('chatbot_memory.SentenceTransformer'):
            chatbot = PDFChatbot("test_key")
            
            text = """MỤC LỤC
Chapter 1: Introduction
This is the first chapter content with some text.

Chapter 2: Advanced Topics
This is the second chapter with more content."""
            
            result = chatbot.powerful_chunking_strategy(text)
            
            assert len(result) > 0
            assert all("heading" in chunk for chunk in result)
            assert all("content" in chunk for chunk in result)
    
    def test_create_embeddings(self):
        """Test embedding creation."""
        with patch('chatbot_memory.genai'), patch('chatbot_memory.SentenceTransformer'):
            mock_embedding_model = Mock()
            mock_embedding_model.encode.return_value = np.array([[1, 2, 3], [4, 5, 6]])
            
            chatbot = PDFChatbot("test_key")
            chatbot.embedding_model = mock_embedding_model
            
            texts = ["text1", "text2"]
            result = chatbot.create_embeddings(texts)
            
            expected = np.array([[1, 2, 3], [4, 5, 6]])
            np.testing.assert_array_equal(result, expected)
            mock_embedding_model.encode.assert_called_once_with(texts, show_progress_bar=True)
    
    @patch('builtins.open', create=True)
    @patch('chatbot_memory.PyPDF2.PdfReader')
    def test_process_pdf_success(self, mock_pdf_reader, mock_open):
        """Test successful PDF processing."""
        # Setup mocks
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        mock_reader = Mock()
        mock_page = Mock()
        mock_page.extract_text.return_value = "Test PDF content with enough text to be chunked properly."
        mock_reader.pages = [mock_page]
        mock_pdf_reader.return_value = mock_reader
        
        with patch('chatbot_memory.genai'), patch('chatbot_memory.SentenceTransformer'):
            mock_embedding_model = Mock()
            mock_embedding_model.encode.return_value = np.array([[1, 2, 3]])
            
            chatbot = PDFChatbot("test_key")
            chatbot.embedding_model = mock_embedding_model
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                tmp_file.write(b'%PDF-1.4\n%Test content\n')
                tmp_file_path = tmp_file.name
            
            try:
                status, files = chatbot.process_pdf(tmp_file_path)
                
                assert "Xử lý thành công" in status
                assert len(chatbot.documents) > 0
                assert len(chatbot.document_metadata) > 0
                assert chatbot.embeddings is not None
                assert os.path.basename(tmp_file_path) in chatbot.processed_files
                
            finally:
                os.unlink(tmp_file_path)
    
    def test_process_pdf_empty_path(self):
        """Test PDF processing with empty path."""
        with patch('chatbot_memory.genai'), patch('chatbot_memory.SentenceTransformer'):
            chatbot = PDFChatbot("test_key")
            
            status, files = chatbot.process_pdf("")
            
            assert "Vui lòng chọn một file PDF" in status
    
    def test_process_pdf_duplicate_file(self):
        """Test PDF processing with duplicate file."""
        with patch('chatbot_memory.genai'), patch('chatbot_memory.SentenceTransformer'):
            chatbot = PDFChatbot("test_key")
            chatbot.processed_files.add("test.pdf")
            
            status, files = chatbot.process_pdf("/path/to/test.pdf")
            
            assert "đã được xử lý" in status
    
    def test_search_relevant_documents_no_embeddings(self):
        """Test search when no embeddings exist."""
        with patch('chatbot_memory.genai'), patch('chatbot_memory.SentenceTransformer'):
            chatbot = PDFChatbot("test_key")
            
            result = chatbot.search_relevant_documents("test query")
            assert result == []
    
    def test_search_relevant_documents_success(self):
        """Test successful document search."""
        with patch('chatbot_memory.genai'), patch('chatbot_memory.SentenceTransformer'):
            mock_embedding_model = Mock()
            mock_embedding_model.encode.return_value = np.array([[1, 0, 0]])
            
            chatbot = PDFChatbot("test_key")
            chatbot.embedding_model = mock_embedding_model
            chatbot.documents = ["doc1", "doc2"]
            chatbot.embeddings = np.array([[1, 0, 0], [0, 1, 0]])
            chatbot.document_metadata = [{"id": 1}, {"id": 2}]
            
            with patch('chatbot_memory.cosine_similarity') as mock_similarity:
                mock_similarity.return_value = np.array([[0.9, 0.1]])
                
                result = chatbot.search_relevant_documents("test query", top_k=1)
                
                assert len(result) == 1
                assert result[0][0] == "doc1"  # Most similar document
                assert result[0][1] == 0.9     # Similarity score
                assert result[0][2] == {"id": 1}  # Metadata
    
    def test_generate_answer_no_documents(self):
        """Test answer generation when no documents are loaded."""
        with patch('chatbot_memory.genai'), patch('chatbot_memory.SentenceTransformer'):
            chatbot = PDFChatbot("test_key")
            
            result_answer, result_history = chatbot.generate_answer("test query", [])
            
            assert "Vui lòng tải lên" in result_answer
            assert result_history == []
    
    def test_generate_answer_low_similarity(self):
        """Test answer generation when similarity is too low."""
        with patch('chatbot_memory.genai'), patch('chatbot_memory.SentenceTransformer'):
            chatbot = PDFChatbot("test_key")
            chatbot.documents = ["doc1"]
            
            with patch.object(chatbot, 'search_relevant_documents') as mock_search:
                mock_search.return_value = [("doc1", 0.1, {"id": 1})]  # Low similarity
                
                result_answer, result_history = chatbot.generate_answer("test query", [])
                
                assert "không tìm thấy thông tin đủ liên quan" in result_answer
                assert result_history == []
    
    def test_generate_answer_success(self):
        """Test successful answer generation."""
        with patch('chatbot_memory.genai'), patch('chatbot_memory.SentenceTransformer'):
            mock_model = Mock()
            mock_response = Mock()
            mock_response.text = "Generated answer"
            mock_model.generate_content.return_value = mock_response
            
            chatbot = PDFChatbot("test_key")
            chatbot.llm = mock_model
            chatbot.documents = ["doc1"]
            
            with patch.object(chatbot, 'search_relevant_documents') as mock_search:
                mock_search.return_value = [("doc1", 0.8, {"source_file": "test.pdf"})]
                
                result_answer, result_history = chatbot.generate_answer("test query", [])
                
                assert result_answer == ""
                assert len(result_history) == 1
                assert result_history[0][0] == "test query"
                assert "Generated answer" in result_history[0][1]
                mock_model.generate_content.assert_called_once()
    
    def test_get_processed_files_markdown_empty(self):
        """Test processed files markdown when no files are processed."""
        with patch('chatbot_memory.genai'), patch('chatbot_memory.SentenceTransformer'):
            chatbot = PDFChatbot("test_key")
            
            result = chatbot._get_processed_files_markdown()
            assert result == "Chưa có tài liệu nào được xử lý."
    
    def test_get_processed_files_markdown_with_files(self):
        """Test processed files markdown with files."""
        with patch('chatbot_memory.genai'), patch('chatbot_memory.SentenceTransformer'):
            chatbot = PDFChatbot("test_key")
            chatbot.processed_files = {"file1.pdf", "file2.pdf"}
            
            result = chatbot._get_processed_files_markdown()
            
            assert "**Các tài liệu trong bộ nhớ:**" in result
            assert "1. file1.pdf" in result or "2. file1.pdf" in result
            assert "1. file2.pdf" in result or "2. file2.pdf" in result
