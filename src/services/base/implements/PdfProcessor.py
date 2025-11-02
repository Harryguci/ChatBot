from src.services.base.interfaces.IDocumentProcessor import IDocumentProcessor
import logging
import PyPDF2


logger = logging.getLogger(__name__)


class PdfProcessor(IDocumentProcessor):
    def extract_content(self, file_path: str) -> str:
        """Extract text from a PDF file, preserving line breaks similar to chatbot logic."""
        try:
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            logger.info("Extracted %d pages from PDF", len(pdf_reader.pages))
            return text
        except Exception as e:
            logger.error("PDF read error: %s", str(e))
            raise