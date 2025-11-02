from abc import ABC, abstractmethod
import os
import logging
import threading
from typing import Optional

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover - optional dependency
    genai = None


logger = logging.getLogger(__name__)


class IGeminiModel(ABC):
    """
    Interface for Gemini models as a singleton pattern.
    """

    @abstractmethod
    def get_model(self):
        """Return the shared GenerativeModel instance."""
        pass


class GeminiModel(IGeminiModel):
    """
    Thread-safe singleton wrapper for a Google Generative AI model.
    Uses environment variable GOOGLE_API_KEY (or GENAI_API_KEY) to configure.
    """

    _instance: Optional["GeminiModel"] = None
    _lock = threading.Lock()

    DEFAULT_MODEL_NAME = 'gemini-2.0-flash-exp'

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, model_name: Optional[str] = None):
        # Avoid re-initialization in singleton
        if getattr(self, "_initialized", False):
            return
        if genai is None:
            raise RuntimeError("google.generativeai is not installed")

        api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GENAI_API_KEY')
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY (or GENAI_API_KEY) is not set")

        try:
            genai.configure(api_key=api_key)
            self._model_name = model_name or self.DEFAULT_MODEL_NAME
            self._model = genai.GenerativeModel(self._model_name)
            logger.info("Gemini model initialized: %s", self._model_name)
        except Exception as e:
            logger.error("Failed to initialize Gemini model: %s", str(e))
            raise
        self._initialized = True

    def get_model(self):
        return self._model

    def model_name(self) -> str:
        return self._model_name