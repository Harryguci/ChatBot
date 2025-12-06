from src.services.base.interfaces.IIngestionService import IIngestionService
from src.services.base.interfaces.IDocumentProcessor import IDocumentProcessor
from src.services.base.implements.PdfProcessor import PdfProcessor
from src.services.base.implements.ImageProcessor import ImageProcessor
from src.services.base.interfaces.GeminiModel import IGeminiModel, GeminiModel

from pathlib import Path
import logging
import os
from typing import Dict, Optional


logger = logging.getLogger(__name__)

# Import enhanced processors with fallback
try:
    from src.services.base.implements.EnhancedPdfProcessor import EnhancedPdfProcessor
    ENHANCED_PDF_AVAILABLE = True
except ImportError:
    logger.warning("EnhancedPdfProcessor not available, using standard PdfProcessor")
    ENHANCED_PDF_AVAILABLE = False


class IngestionService(IIngestionService):
    """
    Service for ingesting documents using strategy processors per file type.
    """

    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}

    def __init__(
        self,
        processors: Optional[Dict[str, IDocumentProcessor]] = None,
        gemini: Optional[IGeminiModel] = None,
        use_enhanced_pdf: bool = None,
    ) -> None:
        # Allow DI for processors and Gemini
        self._gemini = gemini
        self._processors: Dict[str, IDocumentProcessor] = processors or {}

        # Determine whether to use enhanced PDF processor
        if use_enhanced_pdf is None:
            use_enhanced_pdf = os.getenv('USE_ENHANCED_PDF_PROCESSOR', 'true').lower() == 'true'

        # Provide sensible defaults if not injected
        if '.pdf' not in self._processors:
            if use_enhanced_pdf and ENHANCED_PDF_AVAILABLE:
                logger.info("Using EnhancedPdfProcessor with OCR support")
                self._processors['.pdf'] = EnhancedPdfProcessor()
            else:
                logger.info("Using standard PdfProcessor")
                self._processors['.pdf'] = PdfProcessor()

        # Image processor supports Gemini DI
        if 'image' not in self._processors:
            self._processors['image'] = ImageProcessor(gemini=self._gemini or self._lazy_gemini())

    def _lazy_gemini(self) -> IGeminiModel:
        try:
            return GeminiModel()
        except Exception as e:
            logger.warning("Gemini model unavailable: %s", str(e))
            # ImageProcessor will still fall back to Tesseract
            return None  # type: ignore[return-value]

    def process_document(self, file_path: str):
        """
        Process a document by selecting an appropriate processor based on file extension.
        Returns the extracted content as a string.
        """
        ext = self.get_file_extension(file_path)

        try:
            if ext == '.pdf':
                processor = self._processors.get('.pdf')
            elif ext in self.IMAGE_EXTENSIONS:
                processor = self._processors.get('image')
            else:
                raise ValueError(f"Unsupported file type: {ext}")

            if processor is None:
                raise RuntimeError("No processor configured for the given document type")

            content = processor.extract_content(file_path)
            return content
        except Exception as e:
            logger.error("Failed to process document '%s': %s", file_path, str(e))
            raise

    def get_file_extension(self, file_path: str) -> str:
        """Get the lowercase file extension, including dot (e.g., '.pdf')."""
        return Path(file_path).suffix.lower()