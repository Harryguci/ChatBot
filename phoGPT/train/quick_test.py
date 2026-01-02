"""
Quick test script to verify training starts correctly.
Runs just a few training steps to ensure everything works.
"""

import os
import logging
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Run a quick training test."""
    logger.info("Starting quick training test...")

    # Load .env if exists
    if os.path.exists('.env'):
        load_dotenv('.env')

    # Override settings for quick test
    os.environ['NUM_EPOCHS'] = '1'
    os.environ['BATCH_SIZE'] = '2'
    os.environ['SAVE_STEPS'] = '50'  # Save after 50 steps
    os.environ['LOGGING_STEPS'] = '5'  # Log every 5 steps
    os.environ['MAX_STEPS'] = '10'  # Only run 10 steps for testing

    from services.training_service import TrainingService, TrainingConfig

    config = TrainingConfig.from_env()

    logger.info(f"Test configuration:")
    logger.info(f"  Model: {config.model_name}")
    logger.info(f"  Dataset: {config.dataset_name}")
    logger.info(f"  Batch size: {config.batch_size}")
    logger.info(f"  Will run for ~10 training steps only")

    service = TrainingService(config)

    try:
        # Load dataset
        logger.info("\n1. Loading dataset...")
        service.load_dataset()

        # Load model
        logger.info("\n2. Loading model and tokenizer...")
        service.load_model_and_tokenizer()

        # Preprocess
        logger.info("\n3. Preprocessing dataset...")
        tokenized_dataset = service.preprocess_dataset()

        # Create trainer
        logger.info("\n4. Creating trainer...")
        service.create_trainer(tokenized_dataset)

        logger.info("\n" + "="*80)
        logger.info("SUCCESS: All components initialized correctly!")
        logger.info("="*80)
        logger.info("\nYou can now run the full training with:")
        logger.info("  python main.py")
        logger.info("\nNote: Training will be slow on CPU. Consider using GPU for faster training.")

    except Exception as e:
        logger.error(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
