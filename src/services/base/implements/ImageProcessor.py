from src.services.base.interfaces.IDocumentProcessor import IDocumentProcessor
import logging

from PIL import Image
import pytesseract


logger = logging.getLogger(__name__)


class ImageProcessor(IDocumentProcessor):
    """
    Processor for image documents.
    Extracts text from images using Tesseract OCR (offline, no external API).
    """

    def __init__(self):
        pass

    def _extract_with_tesseract(self, image: Image.Image) -> str:
        return pytesseract.image_to_string(image, lang='vie+eng')

    def extract_content(self, file_path: str) -> str:
        """Extract content from an image using Tesseract OCR."""
        try:
            image = Image.open(file_path)
            if image.mode != 'RGB':
                image = image.convert('RGB')
        except Exception as e:
            logger.error("Failed to open image: %s", str(e))
            raise

        # Tesseract OCR (offline)
        try:
            text = self._extract_with_tesseract(image)
            logger.info("Extracted text from image using Tesseract (%d chars)", len(text))
            return text
        except Exception as e:
            logger.error("Image OCR failed: %s", str(e))
            raise