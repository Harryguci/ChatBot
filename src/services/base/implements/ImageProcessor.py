from src.services.base.interfaces.IDocumentProcessor import IDocumentProcessor
from src.services.base.interfaces.GeminiModel import IGeminiModel, GeminiModel
import logging

from PIL import Image
import pytesseract


logger = logging.getLogger(__name__)


class ImageProcessor(IDocumentProcessor):
    """
    Processor for image documents.
    Attempts Gemini Vision first when configured; falls back to Tesseract OCR.
    """

    def __init__(self, gemini: IGeminiModel | None = None):
        self._gemini: IGeminiModel | None = gemini

    def _extract_with_gemini(self, image: Image.Image) -> str:
        # Lazy init when not injected
        if self._gemini is None:
            self._gemini = GeminiModel()
        prompt = (
            "Hãy đọc và trích xuất toàn bộ văn bản có trong hình ảnh này.\n"
            "Bao gồm: 1) Tiêu đề/tiểu đề, 2) Nội dung chính, 3) Ghi chú/chú thích, 4) Số liệu/bảng biểu.\n"
            "Giữ nguyên cấu trúc và định dạng của văn bản. Trả về tiếng Việt."
        )
        model = self._gemini.get_model()
        response = model.generate_content([prompt, image])
        return response.text or ""

    def _extract_with_tesseract(self, image: Image.Image) -> str:
        return pytesseract.image_to_string(image, lang='vie+eng')

    def extract_content(self, file_path: str) -> str:
        """Extract content from an image using Gemini Vision with Tesseract fallback."""
        try:
            image = Image.open(file_path)
            if image.mode != 'RGB':
                image = image.convert('RGB')
        except Exception as e:
            logger.error("Failed to open image: %s", str(e))
            raise

        # Try Gemini first if available and configured
        try:
            text = self._extract_with_gemini(image)
            if text and text.strip():
                logger.info("Extracted text from image using Gemini (%d chars)", len(text))
                return text
        except Exception as e:
            logger.warning("Gemini extraction failed, falling back to Tesseract: %s", str(e))

        # Fallback to Tesseract OCR
        try:
            text = self._extract_with_tesseract(image)
            logger.info("Extracted text from image using Tesseract (%d chars)", len(text))
            return text
        except Exception as e:
            logger.error("Image OCR failed: %s", str(e))
            raise