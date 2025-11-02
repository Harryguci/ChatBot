from typing import List, Optional
import logging
import torch
from PIL import Image
from transformers import AutoModel, AutoProcessor

from src.services.base.interfaces.IVinternEmbeddingService import IVinternEmbeddingService

logger = logging.getLogger(__name__)


class VinternEmbeddingService(IVinternEmbeddingService):
    """
    Implementation of Vintern multimodal embedding service.
    Handles initialization, text embedding, and image embedding using Vintern model.
    """

    def __init__(self, model_name: str = "5CD-AI/Vintern-Embedding-1B"):
        """
        Initialize Vintern embedding service.

        Args:
            model_name: Name of the Vintern model to use
        """
        self._model_name = model_name
        self._enabled = False
        self._device: Optional[str] = None
        self._dtype: Optional[torch.dtype] = None
        self._processor: Optional[AutoProcessor] = None
        self._model: Optional[AutoModel] = None

        self._initialize_model()

    def _initialize_model(self) -> None:
        """Initialize the Vintern model and processor."""
        try:
            self._device = 'cuda' if torch.cuda.is_available() else 'cpu'
            self._dtype = torch.bfloat16 if (
                self._device == 'cuda' and torch.cuda.is_bf16_supported()
            ) else torch.float32

            logger.info(
                "Initializing Vintern model '%s' on device '%s' with dtype '%s'",
                self._model_name, self._device, str(self._dtype)
            )

            self._processor = AutoProcessor.from_pretrained(
                self._model_name,
                trust_remote_code=True
            )

            self._model = AutoModel.from_pretrained(
                self._model_name,
                torch_dtype=self._dtype,
                low_cpu_mem_usage=True,
                trust_remote_code=True,
            ).eval().to(self._device)

            self._enabled = True
            logger.info(
                "✓ Vintern multimodal embeddings ready (%s, dtype=%s)",
                self._device, str(self._dtype)
            )

        except Exception as e:
            self._enabled = False
            self._processor = None
            self._model = None
            logger.warning(
                "Cannot initialize Vintern embeddings: %s. Service will be disabled.",
                str(e)
            )

    def is_enabled(self) -> bool:
        """Check if Vintern embeddings are available."""
        return self._enabled

    def embed_texts(self, texts: List[str]) -> List[torch.Tensor]:
        """
        Create Vintern embeddings for texts.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding tensors
        """
        try:
            if not self._enabled or not self._processor or not self._model:
                logger.warning("Vintern service not enabled, returning empty list")
                return []

            batch_docs = self._processor.process_docs(texts)

            # Move to device
            batch_docs["input_ids"] = batch_docs["input_ids"].to(self._device)
            batch_docs["attention_mask"] = batch_docs["attention_mask"].to(self._device)
            if self._dtype != torch.float32:
                batch_docs["attention_mask"] = batch_docs["attention_mask"].to(self._dtype)

            with torch.no_grad():
                embeddings = self._model(**batch_docs)

            return list(embeddings)

        except Exception as e:
            logger.error("Error creating Vintern embeddings for text: %s", str(e))
            return []

    def embed_images(self, images: List[Image.Image]) -> List[torch.Tensor]:
        """
        Create Vintern embeddings for images.

        Args:
            images: List of PIL Image objects to embed

        Returns:
            List of embedding tensors
        """
        try:
            if not self._enabled or not self._processor or not self._model:
                logger.warning("Vintern service not enabled, returning empty list")
                return []

            batch_images = self._processor.process_images(images)

            # Move to device
            batch_images["pixel_values"] = batch_images["pixel_values"].to(self._device)
            batch_images["input_ids"] = batch_images["input_ids"].to(self._device)
            batch_images["attention_mask"] = batch_images["attention_mask"].to(self._device)

            if self._dtype != torch.float32:
                batch_images["attention_mask"] = batch_images["attention_mask"].to(self._dtype)
                batch_images["pixel_values"] = batch_images["pixel_values"].to(self._dtype)

            with torch.no_grad():
                embeddings = self._model(**batch_images)

            return list(embeddings)

        except Exception as e:
            logger.error("Error creating Vintern embeddings for images: %s", str(e))
            return []

    def get_model_name(self) -> Optional[str]:
        """Get the name of the Vintern model being used."""
        return self._model_name if self._enabled else None

    def get_device(self) -> Optional[str]:
        """Get the device (cuda/cpu) being used."""
        return self._device if self._enabled else None

    def process_query(self, query: str) -> Optional[torch.Tensor]:
        """
        Process a query text and return its embedding.

        Args:
            query: Query text to embed

        Returns:
            Query embedding tensor or None if service is disabled
        """
        try:
            if not self._enabled or not self._processor or not self._model:
                return None

            batch = self._processor.process_queries([query])

            # Move to device/dtype
            if 'input_ids' in batch:
                batch['input_ids'] = batch['input_ids'].to(self._device)
            if 'attention_mask' in batch:
                am = batch['attention_mask'].to(self._device)
                if self._dtype != torch.float32:
                    am = am.to(self._dtype)
                batch['attention_mask'] = am

            with torch.no_grad():
                q_emb = self._model(**batch)

            return q_emb

        except Exception as e:
            logger.error("Error processing query with Vintern: %s", str(e))
            return None

    def score_multi_vector(
        self,
        query_embedding: torch.Tensor,
        doc_embeddings: List[torch.Tensor]
    ) -> Optional[torch.Tensor]:
        """
        Score document embeddings against a query embedding.

        Args:
            query_embedding: Query embedding tensor
            doc_embeddings: List of document embedding tensors

        Returns:
            Tensor of similarity scores or None if service is disabled
        """
        try:
            if not self._enabled or not self._processor:
                return None

            scores = self._processor.score_multi_vector(query_embedding, doc_embeddings)[0]
            return scores

        except Exception as e:
            logger.error("Error scoring with Vintern: %s", str(e))
            return None
