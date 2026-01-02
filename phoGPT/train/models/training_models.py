"""
Database models for training runs and metrics.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import enum

Base = declarative_base()


class TrainingStatus(str, enum.Enum):
    """Training run status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TrainingRun(Base):
    """Model for storing training run information."""
    __tablename__ = "training_runs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    run_name = Column(String(255), unique=True, nullable=False, index=True)
    model_name = Column(String(255), nullable=False)
    dataset_name = Column(String(255), nullable=False)

    # Status tracking
    status = Column(Enum(TrainingStatus), default=TrainingStatus.PENDING, nullable=False)

    # Hyperparameters (stored as JSON)
    hyperparameters = Column(JSON, nullable=True)

    # Training configuration
    learning_rate = Column(Float, nullable=True)
    batch_size = Column(Integer, nullable=True)
    num_epochs = Column(Integer, nullable=True)
    max_steps = Column(Integer, nullable=True)

    # Metrics
    current_epoch = Column(Integer, default=0)
    current_step = Column(Integer, default=0)
    train_loss = Column(Float, nullable=True)
    eval_loss = Column(Float, nullable=True)
    best_metric = Column(Float, nullable=True)

    # Progress tracking
    progress_percentage = Column(Float, default=0.0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Additional info
    output_dir = Column(String(512), nullable=True)
    error_message = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    def __repr__(self):
        return f"<TrainingRun(id={self.id}, name={self.run_name}, status={self.status})>"


class TrainingMetric(Base):
    """Model for storing detailed training metrics per step/epoch."""
    __tablename__ = "training_metrics"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    run_id = Column(Integer, nullable=False, index=True)  # Foreign key to training_runs

    # Step/Epoch info
    step = Column(Integer, nullable=False)
    epoch = Column(Integer, nullable=True)

    # Loss metrics
    loss = Column(Float, nullable=True)
    eval_loss = Column(Float, nullable=True)

    # Performance metrics
    learning_rate = Column(Float, nullable=True)
    gradient_norm = Column(Float, nullable=True)

    # Additional metrics (stored as JSON for flexibility)
    metrics = Column(JSON, nullable=True)

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<TrainingMetric(run_id={self.run_id}, step={self.step}, loss={self.loss})>"
