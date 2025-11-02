from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple

from src.services.base.interfaces.IIngestionService import IIngestionService


class BaseIngestionPipeline(ABC):
    """
    Template Method pattern for document ingestion.
    Skeleton: "Extract -> Embed -> Store".
    """

    def __init__(self, ingestion_service: IIngestionService):
        self._ingestion_service = ingestion_service

    # ===== Template method =====
    def process(self, file_path: str) -> Any:
        """
        Orchestrate: Extract -> Embed -> Store. Returns result of store step.
        """
        self.before_extract(file_path)
        content = self.extract(file_path)
        self.after_extract(content)

        vectors, metadata = self.embed(content, file_path)
        self.after_embed(vectors, metadata)

        result = self.store(content, vectors, metadata, file_path)
        self.after_store(result)
        return result

    # ===== Steps (may be overridden) =====
    def extract(self, file_path: str) -> str:
        """Default extraction delegates to the ingestion service."""
        return self._ingestion_service.process_document(file_path)

    @abstractmethod
    def embed(self, content: str, file_path: str) -> Tuple[Any, Dict[str, Any]]:
        """
        Produce vector representations for the extracted content and return
        (vectors, metadata). Vectors can be a list/array; metadata is a dict.
        """
        pass

    @abstractmethod
    def store(self, content: str, vectors: Any, metadata: Dict[str, Any], file_path: str) -> Any:
        """
        Persist content and vectors (e.g., DB, index). Return a result (e.g., ids).
        """
        pass

    # ===== Hooks (optional overrides) =====
    def before_extract(self, file_path: str) -> None:
        pass

    def after_extract(self, content: str) -> None:
        pass

    def after_embed(self, vectors: Any, metadata: Dict[str, Any]) -> None:
        pass

    def after_store(self, result: Any) -> None:
        pass