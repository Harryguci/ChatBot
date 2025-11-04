"""
Database models for chatbot application using SQLAlchemy.
"""

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, 
    ForeignKey, Index, Float, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from datetime import datetime
import uuid

# Create base class for all models
Base = declarative_base()


class User(Base):
    """User model for chatbot application with Google OAuth support."""

    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=True)

    # Google OAuth fields
    google_id = Column(String(255), unique=True, nullable=True, index=True)
    picture_url = Column(String(500), nullable=True)

    # Role-based access control
    role = Column(String(50), default='user', nullable=False, index=True)  # 'admin', 'user'

    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    conversations = relationship("Conversation", back_populates="user")
    chatbot_sessions = relationship("ChatbotSession", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"


class Document(Base):
    """Document model for stored documents."""
    
    __tablename__ = 'documents'
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_path = Column(String(1000), nullable=True)
    file_size = Column(Integer, nullable=True)
    processing_status = Column(String(50), default='pending', nullable=False)
    extra_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Document(id={self.id}, filename='{self.filename}', status='{self.processing_status}')>"


class DocumentChunk(Base):
    """Document chunk model for text chunks with embeddings."""
    
    __tablename__ = 'document_chunks'
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey('documents.id', ondelete='CASCADE'), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    heading = Column(String(500), nullable=True)
    content = Column(Text, nullable=False)
    content_length = Column(Integer, nullable=False)
    # Using pgvector Vector type for efficient similarity search
    # Dimension 384 is for sentence-transformers models, 1536 for OpenAI embeddings
    embedding = Column(Vector(384), nullable=True)  # Vector embedding using pgvector
    embedding_model = Column(String(255), nullable=True)
    vintern_embedding = Column(Vector(768), nullable=True)  # Vintern multimodal embedding
    vintern_model = Column(String(255), nullable=True)  # Store model version
    extra_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
    
    __table_args__ = (
        Index('ix_document_chunks_doc_index', 'document_id', 'chunk_index'),
        Index(
            'ix_document_chunks_embedding_cosine',
            'embedding',
            postgresql_using='ivfflat',
            postgresql_ops={'embedding': 'vector_cosine_ops'}
        ),
        Index(
            'ix_document_chunks_vintern_embedding_cosine',
            'vintern_embedding',
            postgresql_using='ivfflat',
            postgresql_ops={'vintern_embedding': 'vector_cosine_ops'}
        ),
    )
    
    def __repr__(self):
        return f"<DocumentChunk(id={self.id}, document_id={self.document_id}, chunk_index={self.chunk_index})>"


class Conversation(Base):
    """Conversation model for chat sessions."""
    
    __tablename__ = 'conversations'
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    title = Column(String(255), nullable=True)
    extra_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, session_id='{self.session_id}')>"


class Message(Base):
    """Message model for individual chat messages."""
    
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    content_type = Column(String(50), default='text', nullable=False)  # 'text', 'image', etc.
    extra_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    
    def __repr__(self):
        return f"<Message(id={self.id}, conversation_id={self.conversation_id}, role='{self.role}')>"


class ChatbotSession(Base):
    """Chatbot session model for session state management."""
    
    __tablename__ = 'chatbot_sessions'
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    session_data = Column(JSON, nullable=True)
    last_activity = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="chatbot_sessions")
    
    def __repr__(self):
        return f"<ChatbotSession(id={self.id}, session_id='{self.session_id}')>"


class EmbeddingCache(Base):
    """Embedding cache model for storing computed embeddings."""
    
    __tablename__ = 'embedding_cache'
    
    id = Column(Integer, primary_key=True, index=True)
    content_hash = Column(String(64), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(JSON, nullable=False)  # Array of floats
    model_name = Column(String(255), nullable=False)
    model_version = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Note: Index will be created manually after table creation to avoid conflicts
    # Index('ix_embedding_cache_content_hash', 'content_hash', 'model_name'),
    
    def __repr__(self):
        return f"<EmbeddingCache(id={self.id}, content_hash='{self.content_hash}', model='{self.model_name}')>"


class SystemLog(Base):
    """System log model for application logging."""
    
    __tablename__ = 'system_logs'
    
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(50), nullable=False, index=True)  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    logger_name = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    module = Column(String(255), nullable=True)
    function = Column(String(255), nullable=True)
    line_number = Column(Integer, nullable=True)
    exception_info = Column(Text, nullable=True)
    extra_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self):
        return f"<SystemLog(id={self.id}, level='{self.level}', message='{self.message[:50]}...')>"
