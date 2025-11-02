from abc import ABC, abstractmethod
from typing import List, Optional
import torch
from PIL import Image


class IVinternEmbeddingService(ABC):
    """
    Interface for Vintern multimodal embedding service.
    Provides text and image embedding capabilities using Vintern model.
    """

    @abstractmethod
    def is_enabled(self) -> bool:
        """Check if Vintern embeddings are available."""
        pass

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[torch.Tensor]:
        """
        Create Vintern embeddings for a list of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding tensors
        """
        pass

    @abstractmethod
    def embed_images(self, images: List[Image.Image]) -> List[torch.Tensor]:
        """
        Create Vintern embeddings for a list of images.

        Args:
            images: List of PIL Image objects to embed

        Returns:
            List of embedding tensors
        """
        pass

    @abstractmethod
    def get_model_name(self) -> Optional[str]:
        """Get the name of the Vintern model being used."""
        pass

    @abstractmethod
    def get_device(self) -> Optional[str]:
        """Get the device (cuda/cpu) being used."""
        pass
