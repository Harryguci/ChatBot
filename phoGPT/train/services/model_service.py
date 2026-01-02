from transformers import (
    AutoModel,
    AutoModelForCausalLM,
    AutoModelForSequenceClassification,
    AutoTokenizer,
    AutoConfig,
    PreTrainedModel,
    PreTrainedTokenizer,
)
from typing import Optional, Union, Dict, Any, Tuple
import torch
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Compatibility fix for PhoGPT with newer transformers versions
def _patch_transformers_for_phogpt():
    """
    Patch transformers to add compatibility for PhoGPT model.
    PhoGPT uses old transformers API that has been deprecated.
    """
    try:
        from transformers.models.llama import modeling_llama
        import torch.nn as nn

        # Check if the old classes exist
        if not hasattr(modeling_llama, 'LlamaDynamicNTKScalingRotaryEmbedding'):
            # Create compatibility wrapper class
            class LlamaDynamicNTKScalingRotaryEmbedding(nn.Module):
                def __init__(self, dim, max_position_embeddings=2048, base=10000, scaling_factor=1.0, device=None):
                    super().__init__()
                    # Use the newer LlamaRotaryEmbedding with config
                    from transformers.models.llama.configuration_llama import LlamaConfig

                    # Create a minimal config with required parameters
                    config = LlamaConfig()
                    config.rope_theta = base
                    config.max_position_embeddings = max_position_embeddings
                    config.rope_scaling = {"type": "dynamic", "factor": scaling_factor}

                    self.dim = dim
                    self.max_position_embeddings = max_position_embeddings
                    self.base = base
                    self.rotary_emb = modeling_llama.LlamaRotaryEmbedding(config=config, device=device)

                def forward(self, x, position_ids):
                    return self.rotary_emb(x, position_ids)

            modeling_llama.LlamaDynamicNTKScalingRotaryEmbedding = LlamaDynamicNTKScalingRotaryEmbedding
            logger.info("Patched LlamaDynamicNTKScalingRotaryEmbedding for PhoGPT compatibility")

        if not hasattr(modeling_llama, 'LlamaLinearScalingRotaryEmbedding'):
            # Create compatibility wrapper class
            class LlamaLinearScalingRotaryEmbedding(nn.Module):
                def __init__(self, dim, max_position_embeddings=2048, base=10000, scaling_factor=1.0, device=None):
                    super().__init__()
                    from transformers.models.llama.configuration_llama import LlamaConfig

                    config = LlamaConfig()
                    config.rope_theta = base
                    config.max_position_embeddings = max_position_embeddings
                    config.rope_scaling = {"type": "linear", "factor": scaling_factor}

                    self.dim = dim
                    self.max_position_embeddings = max_position_embeddings
                    self.base = base
                    self.rotary_emb = modeling_llama.LlamaRotaryEmbedding(config=config, device=device)

                def forward(self, x, position_ids):
                    return self.rotary_emb(x, position_ids)

            modeling_llama.LlamaLinearScalingRotaryEmbedding = LlamaLinearScalingRotaryEmbedding
            logger.info("Patched LlamaLinearScalingRotaryEmbedding for PhoGPT compatibility")

    except Exception as e:
        logger.warning(f"Could not patch transformers for PhoGPT: {e}")


# Apply the patch when module is imported
_patch_transformers_for_phogpt()


class ModelService:
    """
    ModelService to manage AI models from HuggingFace Hub.
    Supports loading, configuring, and managing pretrained models and tokenizers.
    """

    def __init__(self, device: Optional[str] = None):
        """
        Initialize ModelService.

        Args:
            device: Device to load models on ('cuda', 'cpu', 'mps'). Auto-detects if None.
        """
        self.model: Optional[PreTrainedModel] = None
        self.tokenizer: Optional[PreTrainedTokenizer] = None
        self.config: Optional[AutoConfig] = None
        self.model_name: Optional[str] = None

        # Auto-detect device if not specified
        if device is None:
            if torch.cuda.is_available():
                self.device = "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                self.device = "mps"
            else:
                self.device = "cpu"
        else:
            self.device = device

        logger.info(f"ModelService initialized with device: {self.device}")

    def load_model(
        self,
        model_name: str,
        model_type: str = "auto",
        cache_dir: Optional[str] = None,
        use_auth_token: Optional[str] = None,
        load_in_8bit: bool = False,
        load_in_4bit: bool = False,
        trust_remote_code: bool = False,
        **kwargs
    ) -> PreTrainedModel:
        """
        Load a pretrained model from HuggingFace Hub.

        Args:
            model_name: Model name or path from HuggingFace Hub
            model_type: Type of model ('auto', 'causal_lm', 'sequence_classification')
            cache_dir: Directory to cache downloaded models
            use_auth_token: HuggingFace API token for private models
            load_in_8bit: Load model in 8-bit precision for reduced memory
            load_in_4bit: Load model in 4-bit precision for reduced memory
            trust_remote_code: Allow custom code from model repository
            **kwargs: Additional arguments for model loading

        Returns:
            Loaded pretrained model
        """
        try:
            # Apply compatibility patch for PhoGPT models
            if "PhoGPT" in model_name or "phogpt" in model_name.lower():
                _patch_transformers_for_phogpt()

            logger.info(f"Loading model: {model_name}")

            # Prepare loading arguments
            # Use torch.float16 for faster loading and less memory usage
            # For CPU, we'll convert after loading since CPU doesn't support float16 well
            load_kwargs = {
                "cache_dir": cache_dir,
                "token": use_auth_token,
                "trust_remote_code": trust_remote_code,
                "low_cpu_mem_usage": True,  # Use less memory when loading on CPU
                "torch_dtype": torch.float16 if self.device != "cpu" else "auto",
                **kwargs
            }

            # Add quantization options if specified
            if load_in_8bit:
                load_kwargs["load_in_8bit"] = True
                load_kwargs["device_map"] = "auto"
                load_kwargs.pop("low_cpu_mem_usage", None)  # Not compatible with quantization
            elif load_in_4bit:
                load_kwargs["load_in_4bit"] = True
                load_kwargs["device_map"] = "auto"
                load_kwargs.pop("low_cpu_mem_usage", None)  # Not compatible with quantization

            # Load model based on type
            logger.info(f"Loading model with type: {model_type}, trust_remote_code: {trust_remote_code}")
            if model_type == "causal_lm":
                logger.info("Using AutoModelForCausalLM.from_pretrained()")
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_name, **load_kwargs
                )
            elif model_type == "sequence_classification":
                logger.info("Using AutoModelForSequenceClassification.from_pretrained()")
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    model_name, **load_kwargs
                )
            else:  # auto
                logger.info("Using AutoModel.from_pretrained()")
                self.model = AutoModel.from_pretrained(model_name, **load_kwargs)

            logger.info(f"Model loaded, now moving to device: {self.device}")

            # Move to device if not using quantization (which handles device automatically)
            if not (load_in_8bit or load_in_4bit):
                self.model = self.model.to(self.device)
                logger.info(f"Model moved to {self.device}")

            self.model_name = model_name
            logger.info(f"Successfully loaded model: {model_name}")

            return self.model

        except Exception as e:
            logger.error(f"Error loading model {model_name}: {str(e)}")
            raise

    def load_tokenizer(
        self,
        tokenizer_name: Optional[str] = None,
        cache_dir: Optional[str] = None,
        use_auth_token: Optional[str] = None,
        trust_remote_code: bool = False,
        **kwargs
    ) -> PreTrainedTokenizer:
        """
        Load a tokenizer from HuggingFace Hub.

        Args:
            tokenizer_name: Tokenizer name (uses model_name if None)
            cache_dir: Directory to cache downloaded tokenizers
            use_auth_token: HuggingFace API token for private models
            trust_remote_code: Allow custom code from tokenizer repository
            **kwargs: Additional arguments for tokenizer loading

        Returns:
            Loaded tokenizer
        """
        try:
            # Use model_name if tokenizer_name not specified
            name = tokenizer_name or self.model_name
            if name is None:
                raise ValueError(
                    "tokenizer_name must be specified or model must be loaded first"
                )

            logger.info(f"Loading tokenizer: {name}")

            self.tokenizer = AutoTokenizer.from_pretrained(
                name,
                cache_dir=cache_dir,
                token=use_auth_token,
                trust_remote_code=trust_remote_code,
                **kwargs
            )

            # Ensure tokenizer has padding token set
            if self.tokenizer.pad_token is None:
                logger.info("Tokenizer does not have pad_token, setting pad_token = eos_token")
                self.tokenizer.pad_token = self.tokenizer.eos_token
                # Also update pad_token_id
                if self.tokenizer.pad_token_id is None and self.tokenizer.eos_token_id is not None:
                    self.tokenizer.pad_token_id = self.tokenizer.eos_token_id

            logger.info(f"Successfully loaded tokenizer: {name}")
            logger.info(f"Tokenizer config: pad_token={self.tokenizer.pad_token}, eos_token={self.tokenizer.eos_token}")
            return self.tokenizer

        except Exception as e:
            logger.error(f"Error loading tokenizer {name}: {str(e)}")
            raise

    def load_model_and_tokenizer(
        self,
        model_name: str,
        model_type: str = "auto",
        cache_dir: Optional[str] = None,
        use_auth_token: Optional[str] = None,
        load_in_8bit: bool = False,
        load_in_4bit: bool = False,
        trust_remote_code: bool = False,
        **kwargs
    ) -> Tuple[PreTrainedModel, PreTrainedTokenizer]:
        """
        Load both model and tokenizer in one call.

        Args:
            model_name: Model name from HuggingFace Hub
            model_type: Type of model ('auto', 'causal_lm', 'sequence_classification')
            cache_dir: Directory to cache downloaded files
            use_auth_token: HuggingFace API token
            load_in_8bit: Load model in 8-bit precision
            load_in_4bit: Load model in 4-bit precision
            trust_remote_code: Allow custom code
            **kwargs: Additional arguments

        Returns:
            Tuple of (model, tokenizer)
        """
        model = self.load_model(
            model_name=model_name,
            model_type=model_type,
            cache_dir=cache_dir,
            use_auth_token=use_auth_token,
            load_in_8bit=load_in_8bit,
            load_in_4bit=load_in_4bit,
            trust_remote_code=trust_remote_code,
            **kwargs
        )

        tokenizer = self.load_tokenizer(
            tokenizer_name=model_name,
            cache_dir=cache_dir,
            use_auth_token=use_auth_token,
            trust_remote_code=trust_remote_code,
        )

        return model, tokenizer

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the loaded model.

        Returns:
            Dictionary containing model information
        """
        if self.model is None:
            raise ValueError("No model loaded. Call load_model() first.")

        info = {
            "model_name": self.model_name,
            "model_type": type(self.model).__name__,
            "device": str(self.device),
            "num_parameters": self.get_num_parameters(),
        }

        if self.config is not None:
            info["config"] = self.config.to_dict()

        return info

    def get_num_parameters(self, trainable_only: bool = False) -> int:
        """
        Get the number of parameters in the model.

        Args:
            trainable_only: Count only trainable parameters

        Returns:
            Number of parameters
        """
        if self.model is None:
            raise ValueError("No model loaded. Call load_model() first.")

        if trainable_only:
            return sum(
                p.numel() for p in self.model.parameters() if p.requires_grad
            )
        else:
            return sum(p.numel() for p in self.model.parameters())

    def print_model_info(self) -> None:
        """
        Print detailed information about the loaded model.
        """
        if self.model is None:
            print("No model loaded.")
            return

        print("=" * 80)
        print("MODEL INFORMATION")
        print("=" * 80)
        print(f"\nModel Name: {self.model_name}")
        print(f"Model Type: {type(self.model).__name__}")
        print(f"Device: {self.device}")
        print(f"Total Parameters: {self.get_num_parameters():,}")
        print(f"Trainable Parameters: {self.get_num_parameters(trainable_only=True):,}")

        if self.tokenizer is not None:
            print(f"\nTokenizer Vocabulary Size: {len(self.tokenizer)}")
            print(f"Padding Token: {self.tokenizer.pad_token}")
            print(f"EOS Token: {self.tokenizer.eos_token}")
            print(f"BOS Token: {self.tokenizer.bos_token}")

        print("\n" + "=" * 80)

    def set_eval_mode(self) -> None:
        """Set model to evaluation mode."""
        if self.model is None:
            raise ValueError("No model loaded.")
        self.model.eval()
        logger.info("Model set to evaluation mode")

    def set_train_mode(self) -> None:
        """Set model to training mode."""
        if self.model is None:
            raise ValueError("No model loaded.")
        self.model.train()
        logger.info("Model set to training mode")

    def save_model(
        self,
        save_path: str,
        save_tokenizer: bool = True,
        **kwargs
    ) -> None:
        """
        Save the model to disk.

        Args:
            save_path: Path to save the model
            save_tokenizer: Whether to save tokenizer as well
            **kwargs: Additional arguments for save_pretrained
        """
        if self.model is None:
            raise ValueError("No model loaded.")

        logger.info(f"Saving model to: {save_path}")
        self.model.save_pretrained(save_path, **kwargs)

        if save_tokenizer and self.tokenizer is not None:
            logger.info(f"Saving tokenizer to: {save_path}")
            self.tokenizer.save_pretrained(save_path)

        logger.info("Model saved successfully")

    def generate_text(
        self,
        prompt: str,
        max_length: int = 100,
        num_return_sequences: int = 1,
        temperature: float = 1.0,
        top_k: int = 50,
        top_p: float = 0.95,
        **kwargs
    ) -> Union[str, list[str]]:
        """
        Generate text using the loaded model.

        Args:
            prompt: Input text prompt
            max_length: Maximum length of generated text
            num_return_sequences: Number of sequences to generate
            temperature: Sampling temperature
            top_k: Top-k sampling parameter
            top_p: Top-p (nucleus) sampling parameter
            **kwargs: Additional generation arguments

        Returns:
            Generated text (string if num_return_sequences=1, else list)
        """
        if self.model is None or self.tokenizer is None:
            raise ValueError("Both model and tokenizer must be loaded.")

        # Tokenize input
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)

        # Generate
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_length=max_length,
                num_return_sequences=num_return_sequences,
                temperature=temperature,
                top_k=top_k,
                top_p=top_p,
                pad_token_id=self.tokenizer.eos_token_id,
                **kwargs
            )

        # Decode outputs
        generated_texts = [
            self.tokenizer.decode(output, skip_special_tokens=True)
            for output in outputs
        ]

        return generated_texts[0] if num_return_sequences == 1 else generated_texts

    def get_device(self) -> str:
        """Get the current device."""
        return self.device

    def to_device(self, device: str) -> None:
        """
        Move model to a different device.

        Args:
            device: Target device ('cuda', 'cpu', 'mps')
        """
        if self.model is None:
            raise ValueError("No model loaded.")

        self.device = device
        self.model = self.model.to(device)
        logger.info(f"Model moved to device: {device}")