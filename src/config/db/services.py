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
                       file_path: Optional[str] = None, 
                       file_size: Optional[int] = None, metadata: Optional[dict] = None) -> Document:
        """Create a new document record."""
        with self.db.get_session() as session:
            document = Document(
                filename=filename,
                original_filename=original_filename,
                file_type=file_type,
                file_path=file_path,
                file_size=file_size,
                extra_metadata=metadata
            )
            session.add(document)
            session.commit()
            session.refresh(document)
            return document
    
    def check_document_exists_by_filename(self, filename: str, original_filename: str) -> Optional[Document]:
        """Check if a document with the same filename exists."""
        with self.db.get_session() as session:
            return session.query(Document).filter(
                (Document.filename == filename) | (Document.original_filename == original_filename)
            ).first()
    
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
    
    def get_all_documents(self) -> List[Document]:
        """Get all documents."""
        with self.db.get_session() as session:
            return session.query(Document).order_by(desc(Document.created_at)).all()
    
    def get_all_processed_documents(self) -> List[Document]:
        """Get all documents that have been successfully processed (have chunks).
        Uses distinct on primary key to avoid DISTINCT over JSON columns (PostgreSQL limitation)."""
        with self.db.get_session() as session:
            documents = (
                session.query(Document)
                .join(DocumentChunk, Document.id == DocumentChunk.document_id)
                .distinct(Document.id)
                .order_by(desc(Document.created_at))
                .all()
            )
            return documents
    
    def get_document_by_filename(self, filename: str) -> Optional[Document]:
        """Get document by filename."""
        with self.db.get_session() as session:
            return session.query(Document).filter(Document.filename == filename).first()
    
    def delete_document_without_chunks(self, document_id: int) -> bool:
        """Delete a document if it has no chunks (incomplete processing)."""
        with self.db.get_session() as session:
            document = session.query(Document).filter(Document.id == document_id).first()
            if document:
                # Check if it has any chunks
                chunk_count = session.query(func.count(DocumentChunk.id)).filter(
                    DocumentChunk.document_id == document_id
                ).scalar()
                if chunk_count == 0:
                    session.delete(document)
                    session.commit()
                    return True
            return False
    
    def delete_document_by_filename(self, filename: str) -> bool:
        """
        Delete a document and all its chunks from the database.
        
        Args:
            filename: The filename of the document to delete
            
        Returns:
            True if document was deleted, False if not found
        """
        with self.db.get_session() as session:
            document = session.query(Document).filter(Document.filename == filename).first()
            if document:
                document_id = document.id
                # Due to CASCADE, chunks will be automatically deleted
                session.delete(document)
                session.commit()
                logger.info(f"Deleted document {document_id} (filename: {filename}) and all its chunks")
                return True
            return False
    
    def get_all_pending_documents(self) -> List[Document]:
        """Get all documents with 'pending' status."""
        with self.db.get_session() as session:
            return session.query(Document).filter(
                Document.processing_status == 'pending'
            ).all()
    
    def get_all_documents_dict(self) -> List[Dict[str, Any]]:
        """Get all documents as dictionaries to avoid session issues."""
        with self.db.get_session() as session:
            documents = session.query(Document).order_by(desc(Document.created_at)).all()
            return [
                {
                    'id': doc.id,
                    'filename': doc.filename,
                    'original_filename': doc.original_filename,
                    'file_type': doc.file_type,
                    'file_path': doc.file_path,
                    'file_size': doc.file_size,
                    'processing_status': doc.processing_status,
                    'extra_metadata': doc.extra_metadata,
                    'created_at': doc.created_at,
                    'updated_at': doc.updated_at
                }
                for doc in documents
            ]


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
                embedding=embedding,  # Will be stored as Vector type
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
    
    def get_all_chunks_with_embeddings(self) -> List[DocumentChunk]:
        """Get all chunks with their embeddings for RAG search."""
        with self.db.get_session() as session:
            return session.query(DocumentChunk).filter(
                DocumentChunk.embedding.isnot(None)
            ).all()
    
    def get_all_chunks_with_vintern_embeddings(self) -> List[DocumentChunk]:
        """Get all chunks with Vintern embeddings."""
        with self.db.get_session() as session:
            return session.query(DocumentChunk).filter(
                DocumentChunk.vintern_embedding.isnot(None)
            ).all()
    
    def update_chunk_embedding(self, chunk_id: int, embedding: List[float], 
                              embedding_model: str) -> bool:
        """Update chunk embedding."""
        with self.db.get_session() as session:
            chunk = session.query(DocumentChunk).filter(DocumentChunk.id == chunk_id).first()
            if chunk:
                chunk.embedding = embedding
                chunk.embedding_model = embedding_model
                session.commit()
                return True
            return False
    
    def update_chunk_vintern_embedding(self, chunk_id: int, vintern_embedding: List[float],
                                      vintern_model: str) -> bool:
        """Update chunk Vintern embedding."""
        with self.db.get_session() as session:
            chunk = session.query(DocumentChunk).filter(DocumentChunk.id == chunk_id).first()
            if chunk:
                chunk.vintern_embedding = vintern_embedding
                chunk.vintern_model = vintern_model
                session.commit()
                return True
            return False
    
    def search_chunks_by_content(self, query: str, limit: int = 10) -> List[DocumentChunk]:
        """Search chunks by content similarity."""
        with self.db.get_session() as session:
            return session.query(DocumentChunk).filter(
                DocumentChunk.content.ilike(f"%{query}%")
            ).limit(limit).all()
    
    def find_similar_chunks_by_embedding(self, query_embedding: List[float], 
                                        limit: int = 5, threshold: float = 0.7) -> List[Tuple[DocumentChunk, float]]:
        """
        Find similar chunks using vector similarity search.
        
        Args:
            query_embedding: Query vector embedding
            limit: Maximum number of results
            threshold: Minimum similarity score (0-1)
            
        Returns:
            List of tuples (DocumentChunk, similarity_score)
        """
        from sqlalchemy import func, text
        from pgvector.sqlalchemy import Vector
        
        with self.db.get_session() as session:
            # Use cosine similarity search using pgvector
            # The <=> operator is cosine distance (lower is more similar)
            # We convert it to similarity score (higher is more similar)
            query = text("""
                SELECT id, document_id, chunk_index, heading, content, content_length,
                       embedding_model, vintern_model, extra_metadata, created_at,
                       embedding,
                       (embedding <=> CAST(:query_vector AS vector)) as distance
                FROM document_chunks
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> CAST(:query_vector AS vector)
                LIMIT :limit
            """)
            
            # Convert list to string format for PostgreSQL
            vector_str = '[' + ','.join(map(str, query_embedding)) + ']'
            
            result = session.execute(query, {
                'query_vector': vector_str,
                'limit': limit
            })
            
            chunks_with_scores = []
            for row in result:
                # Convert distance to similarity score (1 - distance for cosine)
                similarity = max(0.0, 1.0 - float(row.distance))
                if similarity >= threshold:
                    # Get full chunk object
                    chunk = session.query(DocumentChunk).filter(DocumentChunk.id == row.id).first()
                    if chunk:
                        chunks_with_scores.append((chunk, similarity))
            
            return chunks_with_scores
    
    def find_similar_chunks_by_vintern_embedding(self, query_embedding: List[float], 
                                                  limit: int = 5, threshold: float = 0.7) -> List[Tuple[DocumentChunk, float]]:
        """
        Find similar chunks using Vintern vector similarity search.
        
        Args:
            query_embedding: Query vector embedding
            limit: Maximum number of results
            threshold: Minimum similarity score (0-1)
            
        Returns:
            List of tuples (DocumentChunk, similarity_score)
        """
        from sqlalchemy import text
        
        with self.db.get_session() as session:
            query = text("""
                SELECT id, document_id, chunk_index, heading, content, content_length,
                       embedding_model, vintern_model, extra_metadata, created_at,
                       vintern_embedding,
                       (vintern_embedding <=> CAST(:query_vector AS vector)) as distance
                FROM document_chunks
                WHERE vintern_embedding IS NOT NULL
                ORDER BY vintern_embedding <=> CAST(:query_vector AS vector)
                LIMIT :limit
            """)
            
            # Convert list to string format for PostgreSQL
            vector_str = '[' + ','.join(map(str, query_embedding)) + ']'
            
            result = session.execute(query, {
                'query_vector': vector_str,
                'limit': limit
            })
            
            chunks_with_scores = []
            for row in result:
                # Convert distance to similarity score
                similarity = max(0.0, 1.0 - float(row.distance))
                if similarity >= threshold:
                    # Get full chunk object
                    chunk = session.query(DocumentChunk).filter(DocumentChunk.id == row.id).first()
                    if chunk:
                        chunks_with_scores.append((chunk, similarity))
            
            return chunks_with_scores


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
