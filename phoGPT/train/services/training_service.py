import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
)
from datasets import load_dataset, Dataset, DatasetDict
from peft import LoraConfig, get_peft_model, TaskType, PeftModel
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    """Configuration for training parameters loaded from environment variables."""

    # Model and Dataset
    model_name: str
    dataset_name: str

    # Training Hyperparameters
    learning_rate: float
    num_epochs: int
    batch_size: int
    gradient_accumulation_steps: int
    max_length: int
    warmup_steps: int
    weight_decay: float
    logging_steps: int
    save_steps: int
    eval_steps: int

    # Output
    output_dir: str
    save_total_limit: int

    # Optional
    hf_token: Optional[str] = None
    push_to_hub: bool = False
    hub_model_id: Optional[str] = None

    # Training Configuration
    fp16: bool = True
    gradient_checkpointing: bool = False
    dataloader_num_workers: int = 2
    seed: int = 42

    # LoRA Configuration
    use_lora: bool = False
    lora_r: int = 8
    lora_alpha: int = 32
    lora_dropout: float = 0.1
    lora_target_modules: str = "q_proj,v_proj"

    @classmethod
    def from_env(cls) -> "TrainingConfig":
        """Load configuration from environment variables."""
        logger.info("Loading training configuration from environment variables")

        def get_env_bool(key: str, default: bool = False) -> bool:
            """Convert environment variable to boolean."""
            value = os.getenv(key, str(default)).lower()
            return value in ('true', '1', 'yes', 'on')

        def get_env_float(key: str, default: float) -> float:
            """Convert environment variable to float."""
            return float(os.getenv(key, str(default)))

        def get_env_int(key: str, default: int) -> int:
            """Convert environment variable to int."""
            return int(os.getenv(key, str(default)))

        config = cls(
            # Model and Dataset
            model_name=os.getenv("MODEL_NAME", "HuggingFaceTB/SmolLM2-135M"),
            dataset_name=os.getenv("DATASET_NAME", "FinGPT/fingpt-forecaster-dow30-202305-202405"),

            # Training Hyperparameters
            learning_rate=get_env_float("LEARNING_RATE", 2e-5),
            num_epochs=get_env_int("NUM_EPOCHS", 3),
            batch_size=get_env_int("BATCH_SIZE", 4),
            gradient_accumulation_steps=get_env_int("GRADIENT_ACCUMULATION_STEPS", 4),
            max_length=get_env_int("MAX_LENGTH", 512),
            warmup_steps=get_env_int("WARMUP_STEPS", 100),
            weight_decay=get_env_float("WEIGHT_DECAY", 0.01),
            logging_steps=get_env_int("LOGGING_STEPS", 10),
            save_steps=get_env_int("SAVE_STEPS", 500),
            eval_steps=get_env_int("EVAL_STEPS", 500),

            # Output
            output_dir=os.getenv("OUTPUT_DIR", "./output/smolLM2-135M-finetuned"),
            save_total_limit=get_env_int("SAVE_TOTAL_LIMIT", 2),

            # Optional
            hf_token=os.getenv("HF_TOKEN"),
            push_to_hub=get_env_bool("PUSH_TO_HUB", False),
            hub_model_id=os.getenv("HUB_MODEL_ID"),

            # Training Configuration
            fp16=get_env_bool("FP16", True),
            gradient_checkpointing=get_env_bool("GRADIENT_CHECKPOINTING", False),
            dataloader_num_workers=get_env_int("DATALOADER_NUM_WORKERS", 2),
            seed=get_env_int("SEED", 42),

            # LoRA Configuration
            use_lora=get_env_bool("USE_LORA", False),
            lora_r=get_env_int("LORA_R", 8),
            lora_alpha=get_env_int("LORA_ALPHA", 32),
            lora_dropout=get_env_float("LORA_DROPOUT", 0.1),
            lora_target_modules=os.getenv("LORA_TARGET_MODULES", "q_proj,v_proj"),
        )

        logger.info(f"Configuration loaded: {config}")
        return config


class TrainingService:
    """Service for fine-tuning language models with the Hugging Face Trainer."""

    def __init__(self, config: TrainingConfig):
        """
        Initialize TrainingService.

        Args:
            config: Training configuration
        """
        self.config = config
        self.model = None
        self.tokenizer = None
        self.dataset = None
        self.trainer = None

        # Set device
        if torch.cuda.is_available():
            self.device = "cuda"
            logger.info(f"Using CUDA device: {torch.cuda.get_device_name(0)}")
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            self.device = "mps"
            logger.info("Using MPS device")
        else:
            self.device = "cpu"
            logger.info("Using CPU device")

        logger.info(f"TrainingService initialized with device: {self.device}")

    def load_dataset(self) -> DatasetDict:
        """
        Load the dataset from Hugging Face Hub.

        Returns:
            Loaded dataset
        """
        logger.info(f"Loading dataset: {self.config.dataset_name}")

        try:
            self.dataset = load_dataset(self.config.dataset_name)

            logger.info(f"Dataset loaded successfully")
            logger.info(f"Dataset splits: {list(self.dataset.keys())}")

            for split_name, split_data in self.dataset.items():
                logger.info(f"  {split_name}: {len(split_data)} examples")
                if len(split_data) > 0:
                    logger.info(f"    Features: {list(split_data.features.keys())}")
                    logger.info(f"    Sample: {split_data[0]}")

            return self.dataset

        except Exception as e:
            logger.error(f"Error loading dataset: {e}")
            raise

    def load_model_and_tokenizer(self):
        """Load the model and tokenizer."""
        logger.info(f"Loading model: {self.config.model_name}")

        try:
            # Load tokenizer
            logger.info("Loading tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.config.model_name,
                token=self.config.hf_token,
                trust_remote_code=True,
            )

            # Set padding token if not set
            if self.tokenizer.pad_token is None:
                logger.info("Setting pad_token to eos_token")
                self.tokenizer.pad_token = self.tokenizer.eos_token
                self.tokenizer.pad_token_id = self.tokenizer.eos_token_id

            logger.info(f"Tokenizer loaded. Vocab size: {len(self.tokenizer)}")

            # Load model
            logger.info("Loading model...")
            self.model = AutoModelForCausalLM.from_pretrained(
                self.config.model_name,
                token=self.config.hf_token,
                trust_remote_code=True,
                torch_dtype=torch.float16 if self.config.fp16 and self.device != "cpu" else torch.float32,
            )

            # Enable gradient checkpointing if specified
            if self.config.gradient_checkpointing:
                logger.info("Enabling gradient checkpointing")
                self.model.gradient_checkpointing_enable()

            # Apply LoRA if specified
            if self.config.use_lora:
                logger.info("Applying LoRA configuration")
                self._apply_lora()

            # Move model to device
            if not self.config.use_lora:  # LoRA handles device placement
                self.model = self.model.to(self.device)

            # Print model info
            total_params = sum(p.numel() for p in self.model.parameters())
            trainable_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)

            logger.info(f"Model loaded successfully")
            logger.info(f"Total parameters: {total_params:,}")
            logger.info(f"Trainable parameters: {trainable_params:,}")
            logger.info(f"Trainable %: {100 * trainable_params / total_params:.2f}%")

        except Exception as e:
            logger.error(f"Error loading model and tokenizer: {e}")
            raise

    def _apply_lora(self):
        """Apply LoRA (Low-Rank Adaptation) to the model for efficient fine-tuning."""
        logger.info("Configuring LoRA...")

        # Parse target modules
        target_modules = [m.strip() for m in self.config.lora_target_modules.split(",")]

        lora_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=self.config.lora_r,
            lora_alpha=self.config.lora_alpha,
            lora_dropout=self.config.lora_dropout,
            target_modules=target_modules,
            bias="none",
        )

        logger.info(f"LoRA config: r={self.config.lora_r}, alpha={self.config.lora_alpha}, "
                   f"dropout={self.config.lora_dropout}, target_modules={target_modules}")

        self.model = get_peft_model(self.model, lora_config)
        self.model.print_trainable_parameters()

    def preprocess_dataset(self) -> DatasetDict:
        """
        Preprocess the dataset for training.

        Returns:
            Preprocessed dataset
        """
        logger.info("Preprocessing dataset...")

        def preprocess_function(examples):
            """
            Preprocess examples by creating input text from the dataset fields.
            The FinGPT forecaster dataset contains financial data and predictions.
            """
            # Combine relevant fields into a single text input
            # Adjust this based on your dataset structure
            texts = []

            for i in range(len(examples[list(examples.keys())[0]])):
                # Get the example data
                example_dict = {key: examples[key][i] for key in examples.keys()}

                # Format the example as text
                # Customize this based on your dataset structure and task
                text = self._format_example(example_dict)
                texts.append(text)

            # Tokenize
            tokenized = self.tokenizer(
                texts,
                truncation=True,
                max_length=self.config.max_length,
                padding="max_length",
                return_tensors=None,
            )

            # For causal LM, labels are the same as input_ids
            tokenized["labels"] = tokenized["input_ids"].copy()

            return tokenized

        # Preprocess all splits
        logger.info("Tokenizing dataset...")
        tokenized_dataset = self.dataset.map(
            preprocess_function,
            batched=True,
            remove_columns=self.dataset["train"].column_names,
            desc="Tokenizing dataset",
        )

        logger.info(f"Dataset preprocessing complete")
        logger.info(f"Tokenized dataset: {tokenized_dataset}")

        return tokenized_dataset

    def _format_example(self, example: Dict[str, Any]) -> str:
        """
        Format a single example from the dataset into text.

        Args:
            example: Dictionary containing example data

        Returns:
            Formatted text string
        """
        # FinGPT forecaster dataset has: prompt, answer, period, label, symbol
        if 'prompt' in example and 'answer' in example:
            # Format as prompt-completion pair for causal LM
            prompt = example['prompt']
            answer = example['answer']
            return f"{prompt}\n\nAnswer: {answer}"

        # Generic instruction-tuning format
        elif 'text' in example:
            return example['text']
        elif 'input' in example and 'output' in example:
            if 'instruction' in example:
                return f"Instruction: {example['instruction']}\nInput: {example['input']}\nOutput: {example['output']}"
            else:
                return f"Input: {example['input']}\nOutput: {example['output']}"
        else:
            # Fallback: convert to JSON string
            return json.dumps(example)

    def create_trainer(self, tokenized_dataset: DatasetDict) -> Trainer:
        """
        Create the Hugging Face Trainer.

        Args:
            tokenized_dataset: Preprocessed dataset

        Returns:
            Configured Trainer instance
        """
        logger.info("Creating Trainer...")

        # Determine if we have evaluation dataset
        has_eval = "validation" in tokenized_dataset or "test" in tokenized_dataset

        # Ensure save_steps is compatible with eval_steps when load_best_model_at_end is True
        save_steps = self.config.save_steps
        eval_steps = self.config.eval_steps

        if has_eval and (save_steps % eval_steps != 0):
            # Adjust save_steps to be a multiple of eval_steps
            save_steps = eval_steps
            logger.warning(
                f"save_steps ({self.config.save_steps}) is not a multiple of eval_steps ({eval_steps}). "
                f"Adjusting save_steps to {save_steps} to be compatible with load_best_model_at_end."
            )

        # Training arguments
        training_args = TrainingArguments(
            output_dir=self.config.output_dir,
            num_train_epochs=self.config.num_epochs,
            per_device_train_batch_size=self.config.batch_size,
            per_device_eval_batch_size=self.config.batch_size,
            gradient_accumulation_steps=self.config.gradient_accumulation_steps,
            learning_rate=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
            warmup_steps=self.config.warmup_steps,
            logging_dir=f"{self.config.output_dir}/logs",
            logging_steps=self.config.logging_steps,
            save_steps=save_steps,
            eval_steps=eval_steps,
            save_total_limit=self.config.save_total_limit,
            fp16=self.config.fp16 and self.device != "cpu",
            dataloader_num_workers=self.config.dataloader_num_workers,
            seed=self.config.seed,
            push_to_hub=self.config.push_to_hub,
            hub_model_id=self.config.hub_model_id,
            hub_token=self.config.hf_token,
            eval_strategy="steps" if has_eval else "no",
            load_best_model_at_end=has_eval,
            report_to=["tensorboard"],
        )

        logger.info(f"Training arguments: {training_args}")

        # Data collator
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=self.tokenizer,
            mlm=False,  # We're doing causal LM, not masked LM
        )

        # Determine train and eval datasets
        train_dataset = tokenized_dataset["train"]
        eval_dataset = None

        if "validation" in tokenized_dataset:
            eval_dataset = tokenized_dataset["validation"]
        elif "test" in tokenized_dataset:
            eval_dataset = tokenized_dataset["test"]

        # Create Trainer
        self.trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            data_collator=data_collator,
        )

        logger.info("Trainer created successfully")
        return self.trainer

    def train(self):
        """Run the training process."""
        logger.info("=" * 80)
        logger.info("STARTING TRAINING")
        logger.info("=" * 80)

        try:
            # Train
            logger.info("Beginning training...")
            train_result = self.trainer.train()

            logger.info("Training completed!")
            logger.info(f"Training metrics: {train_result.metrics}")

            # Save final model
            logger.info(f"Saving final model to {self.config.output_dir}")
            self.trainer.save_model()

            # Save training metrics
            metrics_file = f"{self.config.output_dir}/training_metrics.json"
            with open(metrics_file, "w") as f:
                json.dump(train_result.metrics, f, indent=2)
            logger.info(f"Training metrics saved to {metrics_file}")

            # Save tokenizer
            self.tokenizer.save_pretrained(self.config.output_dir)
            logger.info(f"Tokenizer saved to {self.config.output_dir}")

            logger.info("=" * 80)
            logger.info("TRAINING COMPLETE")
            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"Error during training: {e}")
            raise

    def evaluate(self):
        """Evaluate the model."""
        if self.trainer is None:
            logger.error("No trainer available. Train the model first.")
            return

        logger.info("Evaluating model...")

        try:
            metrics = self.trainer.evaluate()
            logger.info(f"Evaluation metrics: {metrics}")

            # Save evaluation metrics
            metrics_file = f"{self.config.output_dir}/eval_metrics.json"
            with open(metrics_file, "w") as f:
                json.dump(metrics, f, indent=2)
            logger.info(f"Evaluation metrics saved to {metrics_file}")

            return metrics

        except Exception as e:
            logger.error(f"Error during evaluation: {e}")
            raise

    def run_full_training_pipeline(self):
        """Run the complete training pipeline from start to finish."""
        logger.info("=" * 80)
        logger.info("FINE-TUNING PIPELINE STARTED")
        logger.info("=" * 80)

        try:
            # 1. Load dataset
            logger.info("\nStep 1: Loading dataset...")
            self.load_dataset()

            # 2. Load model and tokenizer
            logger.info("\nStep 2: Loading model and tokenizer...")
            self.load_model_and_tokenizer()

            # 3. Preprocess dataset
            logger.info("\nStep 3: Preprocessing dataset...")
            tokenized_dataset = self.preprocess_dataset()

            # 4. Create trainer
            logger.info("\nStep 4: Creating trainer...")
            self.create_trainer(tokenized_dataset)

            # 5. Train
            logger.info("\nStep 5: Training...")
            self.train()

            # 6. Evaluate (if eval dataset exists)
            if self.trainer.eval_dataset is not None:
                logger.info("\nStep 6: Evaluating...")
                self.evaluate()

            logger.info("\n" + "=" * 80)
            logger.info("FINE-TUNING PIPELINE COMPLETED SUCCESSFULLY")
            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            raise
