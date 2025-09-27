from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import tempfile
import logging
from pathlib import Path

# Import the PDFChatbot class
from ..chatbot_memory import PDFChatbot

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/chatbot", tags=["chatbot"])

# Global chatbot instance
chatbot_instance: Optional[PDFChatbot] = None

# Pydantic models for request/response
class ChatRequest(BaseModel):
    query: str
    chat_history: Optional[List[tuple]] = []

class ChatResponse(BaseModel):
    answer: str
    chat_history: List[tuple]
    confidence: Optional[float] = None

class ProcessPDFResponse(BaseModel):
    status: str
    processed_files: str
    total_chunks: Optional[int] = None

class MemoryStatus(BaseModel):
    processed_files: List[str]
    total_chunks: int
    total_documents: int

# Dependency to get chatbot instance
def get_chatbot() -> PDFChatbot:
    global chatbot_instance
    if chatbot_instance is None:
        # Get API key from environment variable
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            raise HTTPException(
                status_code=500, 
                detail="Google API key not found. Please set GOOGLE_API_KEY environment variable."
            )
        try:
            chatbot_instance = PDFChatbot(google_api_key)
        except Exception as e:
            logger.error(f"Failed to initialize chatbot: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to initialize chatbot: {str(e)}")
    return chatbot_instance

@router.post("/upload-pdf", response_model=ProcessPDFResponse)
async def upload_and_process_pdf(
    file: UploadFile = File(...),
    chatbot: PDFChatbot = Depends(get_chatbot)
):
    """
    Upload and process a PDF file for the chatbot to use in answering questions.
    """
    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            # Process the PDF
            status_message, processed_files_markdown = chatbot.process_pdf(tmp_file_path)
            
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
async def chat_with_documents(
    request: ChatRequest,
    chatbot: PDFChatbot = Depends(get_chatbot)
):
    """
    Ask a question about the uploaded documents and get an answer.
    """
    try:
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # Generate answer
        _, updated_chat_history = chatbot.generate_answer(request.query, request.chat_history)
        
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
                confidence=confidence
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to generate answer")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating answer: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating answer: {str(e)}")

@router.delete("/memory")
async def clear_memory(chatbot: PDFChatbot = Depends(get_chatbot)):
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
async def get_memory_status(chatbot: PDFChatbot = Depends(get_chatbot)):
    """
    Get the current status of the chatbot's memory (processed files, total chunks, etc.).
    """
    try:
        processed_files = list(chatbot.processed_files)
        total_chunks = len(chatbot.documents)
        total_documents = len(chatbot.document_metadata)
        
        return MemoryStatus(
            processed_files=processed_files,
            total_chunks=total_chunks,
            total_documents=total_documents
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
