"""
Pydantic schemas (DTOs) for training API.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

from models.training_models import TrainingStatus


class HyperparametersModel(BaseModel):
    """Hyperparameters for training."""
    learning_rate: float = Field(default=5e-5, description="Learning rate")
    batch_size: int = Field(default=8, description="Batch size per device")
    num_epochs: int = Field(default=3, description="Number of training epochs")
    max_steps: Optional[int] = Field(default=None, description="Maximum training steps")
    warmup_steps: int = Field(default=500, description="Warmup steps")
    weight_decay: float = Field(default=0.01, description="Weight decay")
    gradient_accumulation_steps: int = Field(default=1, description="Gradient accumulation steps")
    max_grad_norm: float = Field(default=1.0, description="Maximum gradient norm")

    # Model loading options
    model_type: str = Field(default="auto", description="Model type (auto, causal_lm, etc.)")
    load_in_8bit: bool = Field(default=False, description="Load model in 8-bit precision")
    load_in_4bit: bool = Field(default=False, description="Load model in 4-bit precision")
    trust_remote_code: bool = Field(default=True, description="Trust remote code")

    # Training options
    save_steps: int = Field(default=500, description="Save checkpoint every N steps")
    eval_steps: int = Field(default=500, description="Evaluate every N steps")
    logging_steps: int = Field(default=100, description="Log every N steps")

    # Additional options
    fp16: bool = Field(default=False, description="Use mixed precision (FP16)")
    bf16: bool = Field(default=False, description="Use bfloat16 precision")
    seed: int = Field(default=42, description="Random seed")

    class Config:
        schema_extra = {
            "example": {
                "learning_rate": 5e-5,
                "batch_size": 8,
                "num_epochs": 3,
                "warmup_steps": 500,
                "save_steps": 500,
                "fp16": True,
            }
        }


class CreateTrainingRunRequest(BaseModel):
    """Request model for creating a training run."""
    run_name: str = Field(..., description="Unique name for the training run")
    model_name: str = Field(..., description="Model name from HuggingFace Hub")
    dataset_name: str = Field(..., description="Dataset name from HuggingFace Hub")
    hyperparameters: HyperparametersModel = Field(default_factory=HyperparametersModel)
    output_dir: Optional[str] = Field(default=None, description="Output directory for checkpoints")
    notes: Optional[str] = Field(default=None, description="Additional notes")

    class Config:
        schema_extra = {
            "example": {
                "run_name": "phobert-finetune-001",
                "model_name": "vinai/phobert-base",
                "dataset_name": "squad_v2",
                "hyperparameters": {
                    "learning_rate": 5e-5,
                    "batch_size": 8,
                    "num_epochs": 3,
                },
                "notes": "Fine-tuning PhoBERT on SQuAD dataset"
            }
        }


class TrainingRunResponse(BaseModel):
    """Response model for training run."""
    id: int
    run_name: str
    model_name: str
    dataset_name: str
    status: str
    progress_percentage: float
    current_epoch: int
    current_step: int
    train_loss: Optional[float]
    eval_loss: Optional[float]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    output_dir: Optional[str]
    error_message: Optional[str]

    class Config:
        orm_mode = True


class TrainingSummaryResponse(BaseModel):
    """Response model for detailed training summary."""
    run_id: int
    run_name: str
    model_name: str
    dataset_name: str
    status: str
    progress: Dict[str, Any]
    metrics: Dict[str, Any]
    hyperparameters: Dict[str, Any]
    timestamps: Dict[str, Any]
    output_dir: Optional[str]
    error_message: Optional[str]
    recent_metrics: List[Dict[str, Any]]


class StatusUpdateRequest(BaseModel):
    """Request model for updating training status."""
    status: TrainingStatus
    error_message: Optional[str] = None


class TrainingStatusResponse(BaseModel):
    """Response model for training status."""
    run_id: int
    run_name: str
    status: str
    progress: Dict[str, Any]
    metrics: Dict[str, Any]
    started_at: Optional[str]
    error_message: Optional[str]


class TrainingMetricResponse(BaseModel):
    """Response model for training metric."""
    step: int
    epoch: Optional[int]
    loss: Optional[float]
    eval_loss: Optional[float]
    learning_rate: Optional[float]
    gradient_norm: Optional[float]
    metrics: Optional[Dict[str, Any]]
    created_at: Optional[str]


class SuccessResponse(BaseModel):
    """Generic success response."""
    message: str
    run_id: int
    status: Optional[str] = None


class MetricLogResponse(BaseModel):
    """Response for logging a metric."""
    message: str
    run_id: int
    step: int
