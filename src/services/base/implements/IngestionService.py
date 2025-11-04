from src.services.base.interfaces.IIngestionService import IIngestionService
from src.services.base.interfaces.IDocumentProcessor import IDocumentProcessor
from src.services.base.implements.PdfProcessor import PdfProcessor
from src.services.base.implements.ImageProcessor import ImageProcessor

from pathlib import Path
import logging
from typing import Dict, Optional


logger = logging.getLogger(__name__)


class IngestionService(IIngestionService):
    """
    Service for ingesting documents using strategy processors per file type.
    """

    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}

    def __init__(
        self,
        processors: Optional[Dict[str, IDocumentProcessor]] = None,
    ) -> None:
        # Allow DI for processors
        self._processors: Dict[str, IDocumentProcessor] = processors or {}

        # Provide sensible defaults if not injected
        if '.pdf' not in self._processors:
            self._processors['.pdf'] = PdfProcessor()
        if 'image' not in self._processors:
            self._processors['image'] = ImageProcessor()

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