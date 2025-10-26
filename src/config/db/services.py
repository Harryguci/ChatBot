"""
Database service layer for chatbot operations.
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func
from sqlalchemy.exc import SQLAlchemyError

from .db_connection import get_database_connection
from .models import (
    Base, User, Document, DocumentChunk, Conversation, 
    Message, ChatbotSession, EmbeddingCache, SystemLog
)

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service layer for database operations."""
    
    def __init__(self):
        self.db = get_database_connection()
    
    def create_tables(self):
        """Create all database tables."""
        try:
            self.db.create_tables(Base)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {str(e)}")
            raise
    
    def drop_tables(self):
        """Drop all database tables."""
        try:
            self.db.drop_tables(Base)
            logger.info("Database tables dropped successfully")
        except Exception as e:
            logger.error(f"Failed to drop database tables: {str(e)}")
            raise


class UserService(DatabaseService):
    """Service for user-related operations."""
    
    def create_user(self, username: str, email: Optional[str] = None, full_name: Optional[str] = None) -> User:
        """Create a new user."""
        with self.db.get_session() as session:
            user = User(
                username=username,
                email=email,
                full_name=full_name
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            return user
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        with self.db.get_session() as session:
            return session.query(User).filter(User.username == username).first()
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        with self.db.get_session() as session:
            return session.query(User).filter(User.id == user_id).first()


class DocumentService(DatabaseService):
    """Service for document-related operations."""
    
    def create_document(self, filename: str, original_filename: str, file_type: str, 
                       content_hash: str, file_path: Optional[str] = None, 
                       file_size: Optional[int] = None, metadata: Optional[dict] = None) -> Document:
        """Create a new document record."""
        with self.db.get_session() as session:
            document = Document(
                filename=filename,
                original_filename=original_filename,
                file_type=file_type,
                file_path=file_path,
                file_size=file_size,
                content_hash=content_hash,
                extra_metadata=metadata
            )
            session.add(document)
            session.commit()
            session.refresh(document)
            return document
    
    def get_document_by_hash(self, content_hash: str) -> Optional[Document]:
        """Get document by content hash."""
        with self.db.get_session() as session:
            return session.query(Document).filter(Document.content_hash == content_hash).first()
    
    def update_document_status(self, document_id: int, status: str) -> bool:
        """Update document processing status."""
        with self.db.get_session() as session:
            document = session.query(Document).filter(Document.id == document_id).first()
            if document:
                document.processing_status = status
                session.commit()
                return True
            return False
    
    def get_documents_by_status(self, status: str) -> List[Document]:
        """Get documents by processing status."""
        with self.db.get_session() as session:
            return session.query(Document).filter(Document.processing_status == status).all()


class DocumentChunkService(DatabaseService):
    """Service for document chunk operations."""
    
    def create_chunk(self, document_id: int, chunk_index: int, heading: Optional[str], 
                    content: str, embedding: Optional[List[float]] = None, 
                    embedding_model: Optional[str] = None, metadata: Optional[dict] = None) -> DocumentChunk:
        """Create a new document chunk."""
        with self.db.get_session() as session:
            chunk = DocumentChunk(
                document_id=document_id,
                chunk_index=chunk_index,
                heading=heading,
                content=content,
                content_length=len(content),
                embedding=embedding,
                embedding_model=embedding_model,
                extra_metadata=metadata
            )
            session.add(chunk)
            session.commit()
            session.refresh(chunk)
            return chunk
    
    def get_chunks_by_document(self, document_id: int) -> List[DocumentChunk]:
        """Get all chunks for a document."""
        with self.db.get_session() as session:
            return session.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id
            ).order_by(DocumentChunk.chunk_index).all()
    
    def search_chunks_by_content(self, query: str, limit: int = 10) -> List[DocumentChunk]:
        """Search chunks by content similarity."""
        with self.db.get_session() as session:
            return session.query(DocumentChunk).filter(
                DocumentChunk.content.ilike(f"%{query}%")
            ).limit(limit).all()


class ConversationService(DatabaseService):
    """Service for conversation operations."""
    
    def create_conversation(self, session_id: str, user_id: Optional[int] = None, 
                           title: Optional[str] = None, metadata: Optional[dict] = None) -> Conversation:
        """Create a new conversation."""
        with self.db.get_session() as session:
            conversation = Conversation(
                session_id=session_id,
                user_id=user_id,
                title=title,
                extra_metadata=metadata
            )
            session.add(conversation)
            session.commit()
            session.refresh(conversation)
            return conversation
    
    def get_conversation_by_session_id(self, session_id: str) -> Optional[Conversation]:
        """Get conversation by session ID."""
        with self.db.get_session() as session:
            return session.query(Conversation).filter(
                Conversation.session_id == session_id
            ).first()
    
    def get_user_conversations(self, user_id: int, limit: int = 50) -> List[Conversation]:
        """Get conversations for a user."""
        with self.db.get_session() as session:
            return session.query(Conversation).filter(
                Conversation.user_id == user_id
            ).order_by(desc(Conversation.updated_at)).limit(limit).all()


class MessageService(DatabaseService):
    """Service for message operations."""
    
    def create_message(self, conversation_id: int, role: str, content: str, 
                      content_type: str = "text", metadata: Optional[dict] = None) -> Message:
        """Create a new message."""
        with self.db.get_session() as session:
            message = Message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                content_type=content_type,
                extra_metadata=metadata
            )
            session.add(message)
            session.commit()
            session.refresh(message)
            return message
    
    def get_conversation_messages(self, conversation_id: int, limit: int = 100) -> List[Message]:
        """Get messages for a conversation."""
        with self.db.get_session() as session:
            return session.query(Message).filter(
                Message.conversation_id == conversation_id
            ).order_by(asc(Message.created_at)).limit(limit).all()


class ChatbotSessionService(DatabaseService):
    """Service for chatbot session operations."""
    
    def create_session(self, session_id: str, user_id: Optional[int] = None, 
                      session_data: Optional[dict] = None) -> ChatbotSession:
        """Create a new chatbot session."""
        with self.db.get_session() as session:
            chatbot_session = ChatbotSession(
                session_id=session_id,
                user_id=user_id,
                session_data=session_data or {}
            )
            session.add(chatbot_session)
            session.commit()
            session.refresh(chatbot_session)
            return chatbot_session
    
    def get_session(self, session_id: str) -> Optional[ChatbotSession]:
        """Get chatbot session by ID."""
        with self.db.get_session() as session:
            return session.query(ChatbotSession).filter(
                ChatbotSession.session_id == session_id
            ).first()
    
    def update_session_data(self, session_id: str, session_data: dict) -> bool:
        """Update session data."""
        with self.db.get_session() as session:
            chatbot_session = session.query(ChatbotSession).filter(
                ChatbotSession.session_id == session_id
            ).first()
            if chatbot_session:
                chatbot_session.session_data = session_data
                chatbot_session.last_activity = datetime.utcnow()
                session.commit()
                return True
            return False


class EmbeddingCacheService(DatabaseService):
    """Service for embedding cache operations."""
    
    def get_cached_embedding(self, content_hash: str, model_name: str) -> Optional[List[float]]:
        """Get cached embedding."""
        with self.db.get_session() as session:
            cache_entry = session.query(EmbeddingCache).filter(
                and_(
                    EmbeddingCache.content_hash == content_hash,
                    EmbeddingCache.model_name == model_name
                )
            ).first()
            return cache_entry.embedding if cache_entry else None
    
    def cache_embedding(self, content_hash: str, content: str, embedding: List[float], 
                       model_name: str, model_version: Optional[str] = None) -> EmbeddingCache:
        """Cache an embedding."""
        with self.db.get_session() as session:
            cache_entry = EmbeddingCache(
                content_hash=content_hash,
                content=content,
                embedding=embedding,
                model_name=model_name,
                model_version=model_version
            )
            session.add(cache_entry)
            session.commit()
            session.refresh(cache_entry)
            return cache_entry


class SystemLogService(DatabaseService):
    """Service for system logging operations."""
    
    def log_event(self, level: str, logger_name: str, message: str, 
                  module: Optional[str] = None, function: Optional[str] = None,
                  line_number: Optional[int] = None, exception_info: Optional[str] = None,
                  extra_data: Optional[dict] = None) -> SystemLog:
        """Log a system event."""
        with self.db.get_session() as session:
            log_entry = SystemLog(
                level=level,
                logger_name=logger_name,
                message=message,
                module=module,
                function=function,
                line_number=line_number,
                exception_info=exception_info,
                extra_data=extra_data
            )
            session.add(log_entry)
            session.commit()
            session.refresh(log_entry)
            return log_entry
    
    def get_logs_by_level(self, level: str, limit: int = 100) -> List[SystemLog]:
        """Get logs by level."""
        with self.db.get_session() as session:
            return session.query(SystemLog).filter(
                SystemLog.level == level
            ).order_by(desc(SystemLog.created_at)).limit(limit).all()


# Global service instances
user_service = UserService()
document_service = DocumentService()
document_chunk_service = DocumentChunkService()
conversation_service = ConversationService()
message_service = MessageService()
chatbot_session_service = ChatbotSessionService()
embedding_cache_service = EmbeddingCacheService()
system_log_service = SystemLogService()
