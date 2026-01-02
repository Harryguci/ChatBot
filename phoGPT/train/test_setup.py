"""
Quick test script to verify the fine-tuning setup is working correctly.
This script tests each component without running the full training pipeline.
"""

import os
import logging
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_imports():
    """Test that all required modules can be imported."""
    logger.info("Testing imports...")
    try:
        from services.training_service import TrainingService, TrainingConfig
        import torch
        from transformers import AutoTokenizer
        from datasets import load_dataset
        logger.info("✓ All imports successful")
        return True
    except Exception as e:
        logger.error(f"✗ Import failed: {e}")
        return False


def test_config():
    """Test configuration loading."""
    logger.info("Testing configuration...")
    try:
        from services.training_service import TrainingConfig

        # Load .env if exists
        if os.path.exists('.env'):
            load_dotenv('.env')

        config = TrainingConfig.from_env()
        logger.info(f"✓ Configuration loaded")
        logger.info(f"  Model: {config.model_name}")
        logger.info(f"  Dataset: {config.dataset_name}")
        logger.info(f"  Epochs: {config.num_epochs}")
        logger.info(f"  Batch size: {config.batch_size}")
        return True
    except Exception as e:
        logger.error(f"✗ Configuration failed: {e}")
        return False


def test_device():
    """Test device availability."""
    logger.info("Testing device availability...")
    try:
        import torch

        if torch.cuda.is_available():
            logger.info(f"✓ CUDA available: {torch.cuda.get_device_name(0)}")
            logger.info(f"  CUDA version: {torch.version.cuda}")
            logger.info(f"  GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            logger.info("✓ MPS (Apple Silicon) available")
        else:
            logger.info("✓ Using CPU (training will be slow)")

        return True
    except Exception as e:
        logger.error(f"✗ Device test failed: {e}")
        return False


def test_dataset_loading():
    """Test loading a small sample from the dataset."""
    logger.info("Testing dataset loading...")
    try:
        from datasets import load_dataset
        from services.training_service import TrainingConfig

        if os.path.exists('.env'):
            load_dotenv('.env')

        config = TrainingConfig.from_env()

        logger.info(f"  Loading dataset: {config.dataset_name}")
        dataset = load_dataset(config.dataset_name)

        logger.info(f"✓ Dataset loaded successfully")
        logger.info(f"  Splits: {list(dataset.keys())}")
        for split_name, split_data in dataset.items():
            logger.info(f"    {split_name}: {len(split_data)} examples")

        # Show sample
        if len(dataset['train']) > 0:
            logger.info(f"  Sample keys: {list(dataset['train'][0].keys())}")

        return True
    except Exception as e:
        logger.error(f"✗ Dataset loading failed: {e}")
        return False


def test_tokenizer():
    """Test loading the tokenizer."""
    logger.info("Testing tokenizer loading...")
    try:
        from transformers import AutoTokenizer
        from services.training_service import TrainingConfig

        if os.path.exists('.env'):
            load_dotenv('.env')

        config = TrainingConfig.from_env()

        logger.info(f"  Loading tokenizer: {config.model_name}")
        tokenizer = AutoTokenizer.from_pretrained(
            config.model_name,
            trust_remote_code=True
        )

        logger.info(f"✓ Tokenizer loaded successfully")
        logger.info(f"  Vocabulary size: {len(tokenizer)}")
        logger.info(f"  Model max length: {tokenizer.model_max_length}")

        # Test tokenization
        test_text = "This is a test sentence for financial forecasting."
        tokens = tokenizer(test_text, return_tensors="pt")
        logger.info(f"  Test tokenization: {test_text}")
        logger.info(f"  Token count: {len(tokens['input_ids'][0])}")

        return True
    except Exception as e:
        logger.error(f"✗ Tokenizer loading failed: {e}")
        return False


def main():
    """Run all tests."""
    logger.info("=" * 80)
    logger.info("TESTING FINE-TUNING SETUP")
    logger.info("=" * 80)

    tests = [
        ("Imports", test_imports),
        ("Configuration", test_config),
        ("Device", test_device),
        ("Dataset Loading", test_dataset_loading),
        ("Tokenizer", test_tokenizer),
    ]

    results = []
    for test_name, test_func in tests:
        logger.info(f"\n{'=' * 80}")
        success = test_func()
        results.append((test_name, success))
        logger.info(f"{'=' * 80}\n")

    # Summary
    logger.info("=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)

    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        logger.info(f"{status}: {test_name}")

    all_passed = all(success for _, success in results)

    logger.info("=" * 80)
    if all_passed:
        logger.info("✓ ALL TESTS PASSED - Ready to run fine-tuning!")
        logger.info("  Run: python main.py")
    else:
        logger.info("✗ SOME TESTS FAILED - Fix issues before running fine-tuning")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
