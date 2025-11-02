from abc import ABC, abstractmethod

class IDocumentProcessor(ABC):
    """
    Use Strategy Pattern to extract content from different types of documents.
    """
    @abstractmethod
    def extract_content(self, file_path: str) -> str:
        pass