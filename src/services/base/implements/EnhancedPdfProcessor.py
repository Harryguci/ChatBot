"""
Enhanced PDF Processor with PyMuPDF and Tesseract OCR support.

This processor provides:
- High-speed text extraction using PyMuPDF (fitz)
- Automatic detection of scanned pages (low text density)
- OCR processing for scanned pages using Tesseract
- Hybrid approach: Direct extraction + OCR fallback
"""

from src.services.base.interfaces.IDocumentProcessor import IDocumentProcessor
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Import with fallback handling
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    logger.warning("PyMuPDF not available, falling back to PyPDF2")
    PYMUPDF_AVAILABLE = False

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    logger.warning("Tesseract OCR not available, OCR features disabled")
    TESSERACT_AVAILABLE = False


class EnhancedPdfProcessor(IDocumentProcessor):
    """
    Enhanced PDF processor supporting both digital and scanned PDFs.

    Features:
    - Fast text extraction with PyMuPDF
    - Automatic scanned page detection
    - OCR fallback for image-based pages
    - Configurable text density threshold
    """

    def __init__(
        self,
        text_threshold: int = 150,
        dpi: int = 300,
        ocr_languages: str = 'vie+eng',
        ocr_enabled: bool = True
    ):
        """
        Initialize the enhanced PDF processor.

        Args:
            text_threshold: Minimum characters per page to skip OCR (default: 150)
            dpi: DPI for rendering pages to images for OCR (default: 300)
            ocr_languages: Tesseract language codes, e.g., 'vie+eng' (default: 'vie+eng')
            ocr_enabled: Enable/disable OCR processing (default: True)
        """
        self.text_threshold = int(os.getenv('TEXT_THRESHOLD', text_threshold))
        self.dpi = dpi
        self.ocr_languages = os.getenv('OCR_LANGUAGES', ocr_languages)
        self.ocr_enabled = os.getenv('OCR_ENABLED', str(ocr_enabled)).lower() == 'true'

        # Validate dependencies
        if not PYMUPDF_AVAILABLE:
            logger.warning(
                "PyMuPDF not installed. Please install: pip install PyMuPDF>=1.23.0"
            )

        if self.ocr_enabled and not TESSERACT_AVAILABLE:
            logger.warning(
                "Tesseract OCR not available. OCR features will be disabled. "
                "Install: pip install pytesseract and apt-get install tesseract-ocr"
            )
            self.ocr_enabled = False

    def extract_content(self, file_path: str) -> str:
        """
        Extract text from PDF using hybrid approach.

        Strategy:
        1. Try PyMuPDF for fast extraction
        2. For each page, check text density
        3. If low density (<threshold chars), apply OCR
        4. Combine results from all pages

        Args:
            file_path: Path to the PDF file

        Returns:
            Extracted text content

        Raises:
            Exception: If PDF processing fails
        """
        if not PYMUPDF_AVAILABLE:
            # Fallback to PyPDF2 if PyMuPDF not available
            return self._fallback_extract(file_path)

        try:
            logger.info(f"Processing PDF with PyMuPDF: {Path(file_path).name}")

            # Open PDF with PyMuPDF
            doc = fitz.open(file_path)
            total_pages = len(doc)
            extracted_text = ""
            ocr_pages_count = 0

            logger.info(f"PDF has {total_pages} pages")

            for page_num in range(total_pages):
                page = doc[page_num]

                # Extract text directly
                page_text = page.get_text()
                text_length = len(page_text.strip())

                # Determine if page needs OCR
                if text_length < self.text_threshold and self.ocr_enabled:
                    logger.debug(
                        f"Page {page_num + 1}: Low text density ({text_length} chars), "
                        f"applying OCR..."
                    )

                    # Apply OCR to this page
                    ocr_text = self._ocr_page(page, page_num)

                    # Use OCR result if it provides more text
                    if len(ocr_text.strip()) > text_length:
                        page_text = ocr_text
                        ocr_pages_count += 1
                        logger.debug(
                            f"Page {page_num + 1}: OCR extracted {len(ocr_text.strip())} chars"
                        )
                else:
                    logger.debug(
                        f"Page {page_num + 1}: Direct extraction ({text_length} chars)"
                    )

                # Add page text with separator
                extracted_text += page_text + "\n\n"

            doc.close()

            logger.info(
                f"Extraction complete: {total_pages} pages total, "
                f"{ocr_pages_count} pages processed with OCR"
            )

            return extracted_text.strip()

        except Exception as e:
            logger.error(f"PyMuPDF extraction failed: {str(e)}")

            # Try fallback to PyPDF2
            try:
                return self._fallback_extract(file_path)
            except Exception as fallback_error:
                logger.error(f"Fallback extraction also failed: {str(fallback_error)}")
                raise Exception(
                    f"PDF extraction failed with both PyMuPDF and PyPDF2: {str(e)}"
                )

    def _ocr_page(self, page, page_num: int) -> str:
        """
        Apply OCR to a single PDF page.

        Args:
            page: fitz.Page object
            page_num: Page number for logging

        Returns:
            OCR extracted text
        """
        if not self.ocr_enabled or not TESSERACT_AVAILABLE:
            return ""

        try:
            # Render page to image at specified DPI
            # Higher DPI = better OCR accuracy but slower
            pix = page.get_pixmap(dpi=self.dpi)

            # Convert to PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Apply OCR with configured languages
            # PSM 3: Fully automatic page segmentation (default)
            ocr_text = pytesseract.image_to_string(
                img,
                lang=self.ocr_languages,
                config='--psm 3 --oem 3'  # OEM 3: Default OCR Engine Mode
            )

            return ocr_text

        except Exception as e:
            logger.warning(f"OCR failed for page {page_num + 1}: {str(e)}")
            return ""

    def _fallback_extract(self, file_path: str) -> str:
        """
        Fallback to PyPDF2 if PyMuPDF fails or is not available.

        Args:
            file_path: Path to PDF file

        Returns:
            Extracted text
        """
        logger.info("Using PyPDF2 fallback for extraction")

        try:
            import PyPDF2

            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)

                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"

            logger.info(f"Extracted {len(pdf_reader.pages)} pages with PyPDF2")
            return text

        except Exception as e:
            logger.error(f"PyPDF2 extraction error: {str(e)}")
            raise

    def get_page_count(self, file_path: str) -> int:
        """
        Get the number of pages in a PDF.

        Args:
            file_path: Path to PDF file

        Returns:
            Number of pages
        """
        if PYMUPDF_AVAILABLE:
            try:
                doc = fitz.open(file_path)
                page_count = len(doc)
                doc.close()
                return page_count
            except Exception:
                pass

        # Fallback to PyPDF2
        try:
            import PyPDF2
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                return len(pdf_reader.pages)
        except Exception as e:
            logger.error(f"Failed to get page count: {str(e)}")
            return 0

    def extract_metadata(self, file_path: str) -> dict:
        """
        Extract PDF metadata.

        Args:
            file_path: Path to PDF file

        Returns:
            Dictionary with metadata
        """
        metadata = {
            'page_count': 0,
            'title': None,
            'author': None,
            'subject': None,
            'creator': None,
            'producer': None,
            'creation_date': None
        }

        if PYMUPDF_AVAILABLE:
            try:
                doc = fitz.open(file_path)
                metadata['page_count'] = len(doc)

                # Extract metadata
                pdf_metadata = doc.metadata
                if pdf_metadata:
                    metadata.update({
                        'title': pdf_metadata.get('title'),
                        'author': pdf_metadata.get('author'),
                        'subject': pdf_metadata.get('subject'),
                        'creator': pdf_metadata.get('creator'),
                        'producer': pdf_metadata.get('producer'),
                        'creation_date': pdf_metadata.get('creationDate')
                    })

                doc.close()
            except Exception as e:
                logger.warning(f"Metadata extraction failed: {str(e)}")

        return metadata
