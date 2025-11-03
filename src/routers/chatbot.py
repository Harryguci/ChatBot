from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import tempfile
import logging
from pathlib import Path
import asyncio
from slowapi import Limiter
from slowapi.util import get_remote_address

# Import the PDFChatbot class
from ..chatbot_memory import Chatbot

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/chatbot", tags=["chatbot"])

# Global chatbot instance
chatbot_instance: Optional[Chatbot] = None
chatbot_lock = asyncio.Lock()

# Pydantic models for request/response
class ChatRequest(BaseModel):
    query: str
    chat_history: Optional[List[tuple]] = []

class ChatResponse(BaseModel):
    answer: str
    chat_history: List[tuple]
    confidence: Optional[float] = None
    source_files: Optional[List[str]] = None

class ProcessPDFResponse(BaseModel):
    status: str
    processed_files: str
    total_chunks: Optional[int] = None

class MemoryStatus(BaseModel):
    processed_files: List[str]
    total_chunks: int
    total_documents: int
    vintern_enabled: bool
    vintern_documents: int
    vintern_text_documents: int
    vintern_image_documents: int

class DocumentInfo(BaseModel):
    filename: str
    file_type: str
    chunks_count: int
    heading: str
    preview: str

class DocumentsListResponse(BaseModel):
    documents: List[DocumentInfo]
    total_documents: int

# Dependency to get chatbot instance with async initialization
async def get_chatbot() -> Chatbot:
    global chatbot_instance

    # Use lock to prevent multiple concurrent initializations
    async with chatbot_lock:
        if chatbot_instance is None:
            # Get API key from environment variable
            google_api_key = os.getenv("GOOGLE_API_KEY")
            if not google_api_key:
                raise HTTPException(
                    status_code=500,
                    detail="Google API key not found. Please set GOOGLE_API_KEY environment variable."
                )
            try:
                logger.info("Initializing chatbot with async pattern...")
                # Use async initialization for better performance
                chatbot_instance = await Chatbot.create_async(google_api_key)
                logger.info("✓ Chatbot initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize chatbot: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Failed to initialize chatbot: {str(e)}")

    return chatbot_instance

@router.post("/upload-document", response_model=ProcessPDFResponse)
@limiter.limit("10/minute")
async def upload_and_process_document(
    request: Request,
    file: UploadFile = File(...),
    chatbot: Chatbot = Depends(get_chatbot)
):
    """
    Upload and process a PDF file or image for the chatbot to use in answering questions.
    Supports PDF, JPG, PNG, BMP, GIF, TIFF, and WEBP files.
    """
    try:
        # Validate file type
        file_extension = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
        supported_extensions = ['pdf', 'jpg', 'jpeg', 'png', 'bmp', 'gif', 'tiff', 'webp']
        
        if file_extension not in supported_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type. Supported formats: {', '.join(supported_extensions)}"
            )
        
        # Create temporary file with appropriate extension
        file_suffix = f'.{file_extension}'
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_suffix) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            # Process the document (PDF or image) using the original filename
            status_message, processed_files_markdown = chatbot.process_document(tmp_file_path, original_filename=file.filename)
            
            # Extract total chunks from status message if available
            total_chunks = None
            if "Tổng số chunks trong bộ nhớ:" in status_message:
                try:
                    chunks_text = status_message.split("Tổng số chunks trong bộ nhớ: ")[1].split(",")[0]
                    total_chunks = int(chunks_text)
                except:
                    pass
            
            return ProcessPDFResponse(
                status=status_message,
                processed_files=processed_files_markdown,
                total_chunks=total_chunks
            )
        
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@router.post("/upload-pdf", response_model=ProcessPDFResponse)
@limiter.limit("10/minute")
async def upload_and_process_pdf(
    request: Request,
    file: UploadFile = File(...),
    chatbot: Chatbot = Depends(get_chatbot)
):
    """
    Upload and process a PDF file for the chatbot to use in answering questions.
    This endpoint is kept for backward compatibility. Use /upload-document for both PDF and images.
    """
    try:
        # Validate file type - only PDF
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported for this endpoint. Use /upload-document for images.")
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            # Process the PDF using the original filename
            status_message, processed_files_markdown = chatbot.process_document(tmp_file_path, original_filename=file.filename)
            
            # Extract total chunks from status message if available
            total_chunks = None
            if "Tổng số chunks trong bộ nhớ:" in status_message:
                try:
                    chunks_text = status_message.split("Tổng số chunks trong bộ nhớ: ")[1].split(",")[0]
                    total_chunks = int(chunks_text)
                except:
                    pass
            
            return ProcessPDFResponse(
                status=status_message,
                processed_files=processed_files_markdown,
                total_chunks=total_chunks
            )
        
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@router.post("/chat", response_model=ChatResponse)
@limiter.limit("30/minute")
async def chat_with_documents(
    http_request: Request,
    request: ChatRequest,
    chatbot: Chatbot = Depends(get_chatbot)
):
    """
    Ask a question about the uploaded documents and get an answer.
    """
    try:
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # Generate answer
        _, updated_chat_history, source_files = chatbot.generate_answer(request.query, request.chat_history)
        
        # Extract the latest answer and confidence score
        if updated_chat_history:
            latest_query, latest_answer = updated_chat_history[-1]
            
            # Extract confidence score from answer if present
            confidence = None
            if "Độ tin cậy của nguồn chính:" in latest_answer:
                try:
                    confidence_text = latest_answer.split("Độ tin cậy của nguồn chính: ")[1].split("%")[0]
                    confidence = float(confidence_text) / 100
                except:
                    pass
            
            return ChatResponse(
                answer=latest_answer,
                chat_history=updated_chat_history,
                confidence=confidence,
                source_files=source_files
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to generate answer")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating answer: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating answer: {str(e)}")

@router.delete("/memory")
async def clear_memory(chatbot: Chatbot = Depends(get_chatbot)):
    """
    Clear all uploaded documents and chat history from the chatbot's memory.
    """
    try:
        chatbot.clear_memory()
        return JSONResponse(
            content={"message": "Memory cleared successfully", "status": "success"}
        )
    except Exception as e:
        logger.error(f"Error clearing memory: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error clearing memory: {str(e)}")

@router.get("/memory/status", response_model=MemoryStatus)
async def get_memory_status(chatbot: Chatbot = Depends(get_chatbot)):
    """
    Get the current status of the chatbot's memory (processed files, total chunks, etc.).
    """
    try:
        processed_files = list(chatbot.processed_files)
        total_chunks = len(chatbot.documents)
        total_documents = len(chatbot.document_metadata)

        # Use vintern_service instead of vintern_enabled
        vintern_enabled = chatbot.vintern_service.is_enabled()
        vintern_meta = chatbot.vintern_doc_metadata if vintern_enabled else []
        vintern_documents = len(vintern_meta)
        vintern_text_documents = sum(1 for m in vintern_meta if m.get('type') == 'text') if vintern_meta else 0
        vintern_image_documents = sum(1 for m in vintern_meta if m.get('type') == 'image') if vintern_meta else 0

        return MemoryStatus(
            processed_files=processed_files,
            total_chunks=total_chunks,
            total_documents=total_documents,
            vintern_enabled=vintern_enabled,
            vintern_documents=vintern_documents,
            vintern_text_documents=vintern_text_documents,
            vintern_image_documents=vintern_image_documents
        )
    except Exception as e:
        logger.error(f"Error getting memory status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting memory status: {str(e)}")

@router.get("/health")
async def health_check():
    """
    Health check endpoint for the chatbot service.
    """
    try:
        global chatbot_instance
        if chatbot_instance is None:
            # Try to initialize chatbot for health check
            google_api_key = os.getenv("GOOGLE_API_KEY")
            if not google_api_key:
                return JSONResponse(
                    status_code=503,
                    content={"status": "unhealthy", "reason": "Google API key not configured"}
                )
        
        return JSONResponse(
            content={"status": "healthy", "service": "chatbot-api"}
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "reason": str(e)}
        )

@router.get("/memorable-documents", response_model=DocumentsListResponse)
async def list_documents(chatbot: Chatbot = Depends(get_chatbot)):
    """
    Get the list of all processed documents with detailed information.
    """
    try:
        documents_info = chatbot.get_documents_list()
        return DocumentsListResponse(
            documents=documents_info,
            total_documents=len(documents_info)
        )
    except Exception as e:
        logger.error(f"Error getting documents list: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting documents list: {str(e)}")

@router.delete("/memorable-documents/{filename:path}")
async def delete_document(filename: str, chatbot: Chatbot = Depends(get_chatbot)):
    """
    Delete a specific document from memory by filename.
    """
    try:
        success, message = chatbot.delete_document(filename)
        
        if success:
            return JSONResponse(
                content={"message": message, "status": "success"}
            )
        else:
            raise HTTPException(status_code=404, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")
