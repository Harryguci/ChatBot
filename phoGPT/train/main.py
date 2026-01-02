import os
import logging
from dotenv import load_dotenv
from services.training_service import TrainingService, TrainingConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main function to run fine-tuning pipeline."""
    logger.info("Starting fine-tuning program for SmolLM2-135M")

    # Load environment variables from .env file
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        logger.info(f"Loading environment variables from {env_path}")
        load_dotenv(env_path)
    else:
        logger.warning(f".env file not found at {env_path}. Using default values.")
        logger.info("Copy .env.example to .env and configure your hyperparameters")

    # Load training configuration from environment variables
    config = TrainingConfig.from_env()

    # Initialize training service
    training_service = TrainingService(config)

    # Run the full training pipeline
    try:
        training_service.run_full_training_pipeline()
        logger.info("Fine-tuning completed successfully!")
        logger.info(f"Model saved to: {config.output_dir}")

    except KeyboardInterrupt:
        logger.warning("Training interrupted by user")
        if training_service.trainer is not None:
            logger.info(f"Partial model saved to: {config.output_dir}")

    except Exception as e:
        logger.error(f"Training failed: {e}")
        raise


if __name__ == "__main__":
    main()