"""
Training API router with endpoints for managing training runs.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
import logging

from config.db_config import get_db_config
from services.training_service import TrainingService
from models.training_models import TrainingStatus

logger = logging.getLogger(__name__)
from schemas.training_schemas import (
    CreateTrainingRunRequest,
    TrainingRunResponse,
    TrainingSummaryResponse,
    StatusUpdateRequest,
    TrainingStatusResponse,
    TrainingMetricResponse,
    SuccessResponse,
    MetricLogResponse,
)

router = APIRouter(prefix="/api/train", tags=["training"])


# Background task for running training
async def run_training_task(run_id: int, dataset_split: Optional[str] = None):
    """
    Background task to prepare and run training.

    Args:
        run_id: Training run ID
        dataset_split: Dataset split to use for training
    """
    # Create a new database session for the background task
    db_config = get_db_config()

    try:
        with db_config.get_session() as session:
            training_service = TrainingService(db_session=session)

            # Prepare training (load model and dataset)
            logger.info(f"Background task: Preparing training for run {run_id}")

            try:
                success = training_service.prepare_training(
                    run_id=run_id,
                    dataset_split=dataset_split,
                )

                if not success:
                    logger.error(f"Background task: Failed to prepare training for run {run_id}")
                    training_service.update_training_status(
                        run_id=run_id,
                        status=TrainingStatus.FAILED,
                        error_message="Failed to prepare training",
                    )
                    return

                # Update status to running
                logger.info(f"Background task: Updating status to RUNNING for run {run_id}")
                training_service.update_training_status(
                    run_id=run_id,
                    status=TrainingStatus.RUNNING,
                )

                logger.info(f"Background task: Training preparation completed for run {run_id}")

                # Execute training loop
                logger.info(f"Background task: About to start training loop for run {run_id}")
                try:
                    logger.info(f"Background task: Calling run_training_loop now...")
                    success = training_service.run_training_loop(run_id=run_id)
                    logger.info(f"Background task: run_training_loop returned: {success}")
                except Exception as training_error:
                    logger.error(f"Background task: Exception in run_training_loop: {str(training_error)}", exc_info=True)
                    raise

                if not success:
                    logger.error(f"Background task: Training failed for run {run_id}")
                else:
                    logger.info(f"Background task: Training completed successfully for run {run_id}")

            except Exception as prep_error:
                logger.error(f"Background task: Exception during preparation for run {run_id}: {str(prep_error)}", exc_info=True)
                training_service.update_training_status(
                    run_id=run_id,
                    status=TrainingStatus.FAILED,
                    error_message=f"Preparation failed: {str(prep_error)}",
                )
                raise

    except Exception as e:
        logger.error(f"Background task: Error in training run {run_id}: {str(e)}")
        with db_config.get_session() as session:
            training_service = TrainingService(db_session=session)
            training_service.update_training_status(
                run_id=run_id,
                status=TrainingStatus.FAILED,
                error_message=str(e),
            )


# Dependency to get database session
def get_db_session():
    """Get database session."""
    db_config = get_db_config()
    with db_config.get_session() as session:
        yield session


# Dependency to get training service
def get_training_service(db: Session = Depends(get_db_session)) -> TrainingService:
    """Get training service instance."""
    return TrainingService(db_session=db)


# API Endpoints

@router.post("/runs", response_model=TrainingRunResponse, status_code=201)
async def create_training_run(
    request: CreateTrainingRunRequest,
    training_service: TrainingService = Depends(get_training_service),
):
    """
    Create a new training run.

    This endpoint creates a new training run with the specified configuration.
    The training run is created in PENDING status and can be started using the start endpoint.

    Args:
        request: Training run configuration

    Returns:
        Created training run information
    """
    try:
        # Convert hyperparameters to dict
        hyperparams_dict = request.hyperparameters.model_dump()

        # Create training run
        training_run = training_service.create_training_run(
            run_name=request.run_name,
            model_name=request.model_name,
            dataset_name=request.dataset_name,
            hyperparameters=hyperparams_dict,
            output_dir=request.output_dir,
        )

        # Add notes if provided
        if request.notes:
            from sqlalchemy import update
            from models.training_models import TrainingRun as TrainingRunModel
            training_service.db_session.execute(
                update(TrainingRunModel)
                .where(TrainingRunModel.id == training_run.id)
                .values(notes=request.notes)
            )
            training_service.db_session.commit()
            training_service.db_session.refresh(training_run)

        return training_run

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create training run: {str(e)}")


@router.get("/runs", response_model=List[TrainingRunResponse])
async def list_training_runs(
    status: Optional[TrainingStatus] = Query(default=None, description="Filter by status"),
    limit: int = Query(default=50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(default=0, ge=0, description="Number of results to skip"),
    training_service: TrainingService = Depends(get_training_service),
):
    """
    List training runs with optional filtering.

    Args:
        status: Filter by training status
        limit: Maximum number of runs to return
        offset: Number of runs to skip (for pagination)

    Returns:
        List of training runs
    """
    try:
        runs = training_service.list_training_runs(
            status=status,
            limit=limit,
            offset=offset,
        )
        return runs

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list training runs: {str(e)}")


@router.get("/runs/{run_id}", response_model=TrainingSummaryResponse)
async def get_training_run(
    run_id: int,
    training_service: TrainingService = Depends(get_training_service),
):
    """
    Get detailed information about a specific training run.

    Args:
        run_id: Training run ID

    Returns:
        Detailed training run information including recent metrics
    """
    try:
        summary = training_service.get_training_summary(run_id)

        if "error" in summary:
            raise HTTPException(status_code=404, detail=summary["error"])

        return summary

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get training run: {str(e)}")


@router.post("/runs/{run_id}/start", response_model=SuccessResponse)
async def start_training_run(
    run_id: int,
    background_tasks: BackgroundTasks,
    dataset_split: Optional[str] = Query(default="train", description="Dataset split to use"),
    training_service: TrainingService = Depends(get_training_service),
):
    """
    Start a training run.

    This endpoint prepares and starts the training process in the background.
    The training will run asynchronously and status can be monitored using the status endpoint.

    Args:
        run_id: Training run ID
        background_tasks: FastAPI background tasks
        dataset_split: Dataset split to use for training

    Returns:
        Status message
    """
    try:
        # Get training run
        training_run = training_service.get_training_run(run_id=run_id)
        if not training_run:
            raise HTTPException(status_code=404, detail="Training run not found")

        # Check if already running or completed
        if training_run.status.value in [TrainingStatus.RUNNING.value, TrainingStatus.COMPLETED.value]:
            raise HTTPException(
                status_code=400,
                detail=f"Training run is already {training_run.status.value}"
            )

        # Update status to pending (will be updated to running by background task)
        training_service.update_training_status(
            run_id=run_id,
            status=TrainingStatus.PENDING,
        )

        # Start training in background
        background_tasks.add_task(run_training_task, run_id, dataset_split)

        logger.info(f"Training run {run_id} queued for execution in background")

        return SuccessResponse(
            message="Training run queued successfully and will start in the background",
            run_id=run_id,
            status=TrainingStatus.PENDING.value,
        )

    except HTTPException:
        raise
    except Exception as e:
        training_service.update_training_status(
            run_id=run_id,
            status=TrainingStatus.FAILED,
            error_message=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Failed to start training: {str(e)}")


@router.get("/runs/{run_id}/status", response_model=TrainingStatusResponse)
async def get_training_status(
    run_id: int,
    training_service: TrainingService = Depends(get_training_service),
):
    """
    Get current status and progress of a training run.

    Args:
        run_id: Training run ID

    Returns:
        Current status and progress information
    """
    try:
        training_run = training_service.get_training_run(run_id=run_id)
        if not training_run:
            raise HTTPException(status_code=404, detail="Training run not found")

        return {
            "run_id": training_run.id,
            "run_name": training_run.run_name,
            "status": training_run.status.value,
            "progress": {
                "percentage": training_run.progress_percentage,
                "current_epoch": training_run.current_epoch,
                "total_epochs": training_run.num_epochs,
                "current_step": training_run.current_step,
                "max_steps": training_run.max_steps,
            },
            "metrics": {
                "train_loss": training_run.train_loss,
                "eval_loss": training_run.eval_loss,
                "best_metric": training_run.best_metric,
            },
            "started_at": training_run.started_at.isoformat() if training_run.started_at is not None else None,
            "error_message": training_run.error_message,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get training status: {str(e)}")


@router.post("/runs/{run_id}/cancel", response_model=SuccessResponse)
async def cancel_training_run(
    run_id: int,
    training_service: TrainingService = Depends(get_training_service),
):
    """
    Cancel a running training run.

    Args:
        run_id: Training run ID

    Returns:
        Cancellation status
    """
    try:
        training_run = training_service.get_training_run(run_id=run_id)
        if not training_run:
            raise HTTPException(status_code=404, detail="Training run not found")

        if training_run.status.value != TrainingStatus.RUNNING.value:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel training run with status: {training_run.status.value}"
            )

        success = training_service.cancel_training_run(run_id)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to cancel training run")

        return SuccessResponse(
            message="Training run cancelled successfully",
            run_id=run_id,
            status=TrainingStatus.CANCELLED.value,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel training: {str(e)}")


@router.patch("/runs/{run_id}/status", response_model=SuccessResponse)
async def update_training_status(
    run_id: int,
    request: StatusUpdateRequest,
    training_service: TrainingService = Depends(get_training_service),
):
    """
    Manually update training run status.

    This endpoint allows manual status updates, useful for external training processes.

    Args:
        run_id: Training run ID
        request: Status update request

    Returns:
        Updated status
    """
    try:
        success = training_service.update_training_status(
            run_id=run_id,
            status=request.status,
            error_message=request.error_message,
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update status")

        return SuccessResponse(
            message="Status updated successfully",
            run_id=run_id,
            status=request.status.value,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update status: {str(e)}")


@router.get("/runs/{run_id}/metrics", response_model=List[TrainingMetricResponse])
async def get_training_metrics(
    run_id: int,
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of metrics"),
    training_service: TrainingService = Depends(get_training_service),
):
    """
    Get training metrics for a specific run.

    Args:
        run_id: Training run ID
        limit: Maximum number of metrics to return

    Returns:
        List of training metrics
    """
    try:
        metrics = training_service.get_training_metrics(run_id, limit=limit)

        return [
            TrainingMetricResponse(
                step=m.step,
                epoch=m.epoch,
                loss=m.loss,
                eval_loss=m.eval_loss,
                learning_rate=m.learning_rate,
                gradient_norm=m.gradient_norm,
                metrics=m.metrics,
                created_at=m.created_at.isoformat() if m.created_at else None,
            )
            for m in metrics
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@router.delete("/runs/{run_id}", response_model=SuccessResponse)
async def delete_training_run(
    run_id: int,
    training_service: TrainingService = Depends(get_training_service),
):
    """
    Delete a training run and all associated metrics.

    Warning: This action cannot be undone.

    Args:
        run_id: Training run ID

    Returns:
        Deletion status
    """
    try:
        training_run = training_service.get_training_run(run_id=run_id)
        if not training_run:
            raise HTTPException(status_code=404, detail="Training run not found")

        # Don't allow deleting running training
        if training_run.status.value == TrainingStatus.RUNNING.value:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete running training run. Cancel it first."
            )

        success = training_service.delete_training_run(run_id)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete training run")

        return SuccessResponse(
            message="Training run deleted successfully",
            run_id=run_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete training run: {str(e)}")


@router.post("/runs/{run_id}/log-metric", response_model=MetricLogResponse)
async def log_training_metric(
    run_id: int,
    step: int,
    epoch: Optional[int] = None,
    loss: Optional[float] = None,
    eval_loss: Optional[float] = None,
    learning_rate: Optional[float] = None,
    gradient_norm: Optional[float] = None,
    additional_metrics: Optional[Dict[str, Any]] = None,
    training_service: TrainingService = Depends(get_training_service),
):
    """
    Log a training metric for a specific step.

    This endpoint is used by training processes to log metrics during training.

    Args:
        run_id: Training run ID
        step: Training step
        epoch: Current epoch
        loss: Training loss
        eval_loss: Evaluation loss
        learning_rate: Current learning rate
        gradient_norm: Gradient norm
        additional_metrics: Additional metrics

    Returns:
        Success status
    """
    try:
        success = training_service.log_training_metric(
            run_id=run_id,
            step=step,
            epoch=epoch,
            loss=loss,
            eval_loss=eval_loss,
            learning_rate=learning_rate,
            gradient_norm=gradient_norm,
            additional_metrics=additional_metrics,
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to log metric")

        # Also update the training run's current metrics
        training_service.update_training_status(
            run_id=run_id,
            status=TrainingStatus.RUNNING,
            current_step=step,
            current_epoch=epoch,
            train_loss=loss,
            eval_loss=eval_loss,
        )

        return MetricLogResponse(
            message="Metric logged successfully",
            run_id=run_id,
            step=step,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log metric: {str(e)}")
