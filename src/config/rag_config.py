"""
RAG System Configuration Management.

This module centralizes all configuration settings for the enhanced RAG system,
providing type-safe access to environment variables with sensible defaults.
"""

import os
from typing import Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class RAGConfig:
    """Configuration for RAG system enhancements."""

    # FAISS Configuration
    use_faiss: bool = False
    faiss_index_path: str = "./data/faiss"

    # Chunking Configuration
    chunk_size: int = 1500
    chunk_overlap: int = 200
    use_langchain_chunking: bool = True

    # OCR Configuration
    ocr_enabled: bool = True
    ocr_languages: str = "vie+eng"
    text_threshold: int = 150  # Minimum characters before OCR triggers

    # Query Enhancement
    multi_query_enabled: bool = True
    num_query_variations: int = 3

    # Search Configuration
    default_top_k: int = 5
    similarity_threshold: float = 0.1
    recency_weight: float = 0.15

    # PDF Processing
    pdf_dpi: int = 300  # DPI for OCR rendering
    use_enhanced_pdf_processor: bool = True

    # Model Configuration
    text_embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    llm_model: str = "gemini-2.5-flash-lite"

    @classmethod
    def from_env(cls) -> 'RAGConfig':
        """
        Load configuration from environment variables.

        Returns:
            RAGConfig instance with values from environment
        """
        config = cls()

        # FAISS settings
        config.use_faiss = os.getenv('USE_FAISS', 'false').lower() == 'true'
        config.faiss_index_path = os.getenv('FAISS_INDEX_PATH', './data/faiss')

        # Chunking settings
        try:
            config.chunk_size = int(os.getenv('CHUNK_SIZE', '1500'))
        except ValueError:
            logger.warning("Invalid CHUNK_SIZE, using default: 1500")
            config.chunk_size = 1500

        try:
            config.chunk_overlap = int(os.getenv('CHUNK_OVERLAP', '200'))
        except ValueError:
            logger.warning("Invalid CHUNK_OVERLAP, using default: 200")
            config.chunk_overlap = 200

        config.use_langchain_chunking = (
            os.getenv('USE_LANGCHAIN_CHUNKING', 'true').lower() == 'true'
        )

        # OCR settings
        config.ocr_enabled = os.getenv('OCR_ENABLED', 'true').lower() == 'true'
        config.ocr_languages = os.getenv('OCR_LANGUAGES', 'vie+eng')

        try:
            config.text_threshold = int(os.getenv('TEXT_THRESHOLD', '150'))
        except ValueError:
            logger.warning("Invalid TEXT_THRESHOLD, using default: 150")
            config.text_threshold = 150

        # Query enhancement
        config.multi_query_enabled = (
            os.getenv('MULTI_QUERY_ENABLED', 'true').lower() == 'true'
        )

        try:
            config.num_query_variations = int(os.getenv('NUM_QUERY_VARIATIONS', '3'))
        except ValueError:
            logger.warning("Invalid NUM_QUERY_VARIATIONS, using default: 3")
            config.num_query_variations = 3

        # Search settings
        try:
            config.default_top_k = int(os.getenv('DEFAULT_TOP_K', '5'))
        except ValueError:
            logger.warning("Invalid DEFAULT_TOP_K, using default: 5")
            config.default_top_k = 5

        try:
            config.similarity_threshold = float(os.getenv('SIMILARITY_THRESHOLD', '0.1'))
        except ValueError:
            logger.warning("Invalid SIMILARITY_THRESHOLD, using default: 0.1")
            config.similarity_threshold = 0.1

        try:
            config.recency_weight = float(os.getenv('RECENCY_WEIGHT', '0.15'))
        except ValueError:
            logger.warning("Invalid RECENCY_WEIGHT, using default: 0.15")
            config.recency_weight = 0.15

        # PDF processing
        try:
            config.pdf_dpi = int(os.getenv('PDF_DPI', '300'))
        except ValueError:
            logger.warning("Invalid PDF_DPI, using default: 300")
            config.pdf_dpi = 300

        config.use_enhanced_pdf_processor = (
            os.getenv('USE_ENHANCED_PDF_PROCESSOR', 'true').lower() == 'true'
        )

        # Model configuration
        config.text_embedding_model = os.getenv(
            'TEXT_EMBEDDING_MODEL',
            'paraphrase-multilingual-MiniLM-L12-v2'
        )
        config.llm_model = os.getenv('LLM_MODEL', 'gemini-2.5-flash-lite')

        logger.info("RAG Configuration loaded:")
        logger.info(f"  - FAISS enabled: {config.use_faiss}")
        logger.info(f"  - LangChain chunking: {config.use_langchain_chunking}")
        logger.info(f"  - Chunk size: {config.chunk_size}")
        logger.info(f"  - OCR enabled: {config.ocr_enabled}")
        logger.info(f"  - MultiQuery enabled: {config.multi_query_enabled}")
        logger.info(f"  - Enhanced PDF processor: {config.use_enhanced_pdf_processor}")

        return config

    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            'faiss': {
                'enabled': self.use_faiss,
                'index_path': self.faiss_index_path
            },
            'chunking': {
                'use_langchain': self.use_langchain_chunking,
                'chunk_size': self.chunk_size,
                'chunk_overlap': self.chunk_overlap
            },
            'ocr': {
                'enabled': self.ocr_enabled,
                'languages': self.ocr_languages,
                'text_threshold': self.text_threshold,
                'pdf_dpi': self.pdf_dpi
            },
            'query': {
                'multi_query_enabled': self.multi_query_enabled,
                'num_variations': self.num_query_variations
            },
            'search': {
                'default_top_k': self.default_top_k,
                'similarity_threshold': self.similarity_threshold,
                'recency_weight': self.recency_weight
            },
            'models': {
                'text_embedding': self.text_embedding_model,
                'llm': self.llm_model
            },
            'pdf_processing': {
                'use_enhanced_processor': self.use_enhanced_pdf_processor,
                'dpi': self.pdf_dpi
            }
        }

    def validate(self) -> bool:
        """
        Validate configuration settings.

        Returns:
            True if configuration is valid, False otherwise
        """
        valid = True

        # Validate chunk settings
        if self.chunk_size < 100:
            logger.error(f"CHUNK_SIZE too small: {self.chunk_size} (minimum: 100)")
            valid = False

        if self.chunk_overlap >= self.chunk_size:
            logger.error(
                f"CHUNK_OVERLAP ({self.chunk_overlap}) must be less than "
                f"CHUNK_SIZE ({self.chunk_size})"
            )
            valid = False

        # Validate search settings
        if not 0.0 <= self.similarity_threshold <= 1.0:
            logger.error(
                f"SIMILARITY_THRESHOLD must be between 0 and 1: {self.similarity_threshold}"
            )
            valid = False

        if not 0.0 <= self.recency_weight <= 1.0:
            logger.error(
                f"RECENCY_WEIGHT must be between 0 and 1: {self.recency_weight}"
            )
            valid = False

        # Validate query settings
        if self.num_query_variations < 1 or self.num_query_variations > 10:
            logger.warning(
                f"NUM_QUERY_VARIATIONS ({self.num_query_variations}) should be "
                f"between 1 and 10"
            )

        # Validate PDF settings
        if self.pdf_dpi < 72 or self.pdf_dpi > 600:
            logger.warning(
                f"PDF_DPI ({self.pdf_dpi}) is outside recommended range (72-600)"
            )

        return valid


# Global configuration instance
_config: Optional[RAGConfig] = None


def get_config() -> RAGConfig:
    """
    Get the global RAG configuration instance.

    Returns:
        RAGConfig instance
    """
    global _config

    if _config is None:
        _config = RAGConfig.from_env()

        # Validate configuration
        if not _config.validate():
            logger.warning("Configuration validation failed, using defaults where possible")

    return _config


def reload_config() -> RAGConfig:
    """
    Reload configuration from environment variables.

    Returns:
        New RAGConfig instance
    """
    global _config
    _config = None
    return get_config()
