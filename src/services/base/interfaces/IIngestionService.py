from abc import ABC, abstractmethod

class IIngestionService(ABC):
    """
    Interface for ingestion services.
    """
    @abstractmethod
    def process_document(self, file_path: str):
        pass

    @abstractmethod
    def get_file_extension(self, file_path: str) -> str:
        pass