# PhoGPT Training & Fine-tuning

This module provides a comprehensive framework for training and fine-tuning Vietnamese language models using the PhoGPT architecture. It includes services for data management, model handling, and database integration.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Training API](#training-api)
- [Services](#services)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Development](#development)

## Overview

The PhoGPT training module is designed to streamline the process of fine-tuning large language models for Vietnamese language tasks. It provides modular services for:

- Dataset loading and preprocessing
- Model management and inference
- Database operations for training metadata
- Configuration management

## Features

- **RESTful Training API**: Complete API for managing training runs with FastAPI
- **Database Tracking**: PostgreSQL integration for storing training runs and metrics
- **Progress Monitoring**: Real-time status updates and progress tracking
- **DataManager Service**: Load and manage datasets from HuggingFace Hub or local sources
- **ModelService**: Handle model and tokenizer loading with quantization support
- **Configurable Hyperparameters**: Set all training parameters via API requests
- **Metrics Logging**: Track training progress with detailed metrics
- **Flexible Configuration**: Environment-based configuration with sensible defaults
- **Type Safety**: Comprehensive type hints for better development experience
- **Auto-generated Documentation**: Interactive API docs at `/docs`

## Installation

### Prerequisites

- Python 3.8+
- PostgreSQL 12+ (optional, for database features)
- CUDA-capable GPU (recommended for training)

### Install Dependencies

```bash
cd phoGPT/train
pip install -r requirements.txt
```

### Optional Dependencies

For 8-bit/4-bit quantization support:
```bash
pip install bitsandbytes>=0.41.0 accelerate>=0.20.0
```

For specific tokenizers:
```bash
pip install sentencepiece>=0.1.99 protobuf>=3.20.0
```

## Project Structure

```
phoGPT/train/
├── app.py                    # FastAPI application entry point
├── init_db.py               # Database initialization script
├── main.py                   # Example entry point
├── requirements.txt          # Python dependencies
├── README.md                # This file
├── TRAINING_API.md          # Comprehensive API documentation
├── config/
│   └── db_config.py          # Database configuration
├── models/
│   └── training_models.py    # SQLAlchemy database models
├── schemas/
│   └── training_schemas.py   # Pydantic request/response schemas
├── services/
│   ├── data_manager.py       # Dataset management
│   ├── model_service.py      # Model management
│   └── training_service.py   # Training orchestration
├── routers/
│   └── train_router.py       # Training API endpoints
├── migrations/
│   ├── __init__.py
│   ├── README.md             # Comprehensive migration documentation
│   ├── MIGRATION_GUIDE.md    # Quick reference guide
│   ├── migrate.py            # Migration runner CLI
│   ├── 20251228_001_initial_schema.py
│   └── 20251228_002_example_add_column.py
└── frontend/
    ├── IMPLEMENTATION_PLAN.md
    ├── IMPLEMENTATION_SUMMARY.md
    └── my-app/              # Next.js dashboard
```

## Training API

For complete API documentation including all endpoints, request/response schemas, and usage examples, see **[TRAINING_API.md](TRAINING_API.md)**.

### Quick API Example

```bash
# Start the API server
python app.py

# Visit http://localhost:8000/docs for interactive API documentation
```

```python
import requests

# Create a training run
response = requests.post("http://localhost:8000/api/train/runs", json={
    "run_name": "my-first-training",
    "model_name": "vinai/phobert-base",
    "dataset_name": "squad_v2",
    "hyperparameters": {
        "learning_rate": 5e-5,
        "batch_size": 8,
        "num_epochs": 3
    }
})

run_id = response.json()["id"]

# Start training
requests.post(f"http://localhost:8000/api/train/runs/{run_id}/start")

# Check status
status = requests.get(f"http://localhost:8000/api/train/runs/{run_id}/status")
print(status.json())
```

## Fine-Tuning SmolLM2-135M

This project now includes a complete fine-tuning pipeline for the **HuggingFaceTB/SmolLM2-135M** model using the **FinGPT fingpt-forecaster-dow30-202305-202405** dataset.

### Quick Fine-Tuning Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Hyperparameters**
   ```bash
   cp .env.example .env
   # Edit .env to customize training hyperparameters
   ```

3. **Run Fine-Tuning**
   ```bash
   python main.py
   ```

### Fine-Tuning Configuration

The `.env` file contains all training hyperparameters:

```env
# Model Configuration
MODEL_NAME=HuggingFaceTB/SmolLM2-135M
DATASET_NAME=FinGPT/fingpt-forecaster-dow30-202305-202405

# Training Hyperparameters
LEARNING_RATE=2e-5
NUM_EPOCHS=3
BATCH_SIZE=4
GRADIENT_ACCUMULATION_STEPS=4
MAX_LENGTH=512
WARMUP_STEPS=100
WEIGHT_DECAY=0.01
LOGGING_STEPS=10
SAVE_STEPS=500
EVAL_STEPS=500

# Output
OUTPUT_DIR=./output/smolLM2-135M-finetuned
SAVE_TOTAL_LIMIT=2

# Training Configuration
FP16=true
GRADIENT_CHECKPOINTING=false
DATALOADER_NUM_WORKERS=2
SEED=42

# LoRA Configuration (for efficient fine-tuning)
USE_LORA=false
LORA_R=8
LORA_ALPHA=32
LORA_DROPOUT=0.1
LORA_TARGET_MODULES=q_proj,v_proj
```

### Fine-Tuning Features

- **Environment-based Configuration**: All hyperparameters loaded from `.env`
- **Comprehensive Logging**: Detailed logging at each training step
- **LoRA Support**: Efficient fine-tuning with Low-Rank Adaptation
- **Quantization**: Support for 8-bit and 4-bit quantization
- **TensorBoard**: Training visualization and monitoring
- **Gradient Checkpointing**: Memory-efficient training
- **Automatic Device Detection**: CUDA/MPS/CPU

### Monitoring Training

Training metrics are logged to TensorBoard:

```bash
tensorboard --logdir=./output/smolLM2-135M-finetuned/logs
```

Open http://localhost:6006 to view training progress.

### Memory Optimization

For CUDA out-of-memory errors:

1. Enable LoRA: `USE_LORA=true`
2. Reduce batch size: `BATCH_SIZE=2`
3. Increase gradient accumulation: `GRADIENT_ACCUMULATION_STEPS=8`
4. Enable gradient checkpointing: `GRADIENT_CHECKPOINTING=true`

## Quick Start

### 1. Set Up Environment Variables

Create a `.env` file in the project root:

```env
# Database Configuration (optional)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=phogpt_db
DB_USER=postgres
DB_PASSWORD=your_password

# Connection Pool Settings
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600

# Debug Settings
DB_ECHO=false
```

### 2. Initialize Database

```bash
# Create database tables
python init_db.py
```

**Migration Files**: Python migration files are available in the `migrations/` folder. See [migrations/README.md](migrations/README.md) for comprehensive documentation or [migrations/MIGRATION_GUIDE.md](migrations/MIGRATION_GUIDE.md) for a quick reference.

You can also use the migration CLI:
```bash
# Check migration status
python migrations/migrate.py status

# Apply all migrations
python migrations/migrate.py upgrade
```

### 3. Start API Server

```bash
# Development mode with auto-reload
python app.py

# Or use uvicorn directly
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 4. Load and Explore a Dataset (Programmatic)

```python
from services.data_manager import DataManager

# Initialize DataManager
dm = DataManager()

# Load dataset from HuggingFace Hub
dm.load_data("FinGPT/fingpt-forecaster-dow30-202305-202405")

# Print dataset information
dm.print_dataset_info()

# Get specific split
train_data = dm.get_split("train")
print(f"Training examples: {len(train_data)}")
```

### 5. Load a Model (Programmatic)

```python
from services.model_service import ModelService

# Initialize ModelService (auto-detects GPU/CPU)
ms = ModelService()

# Load model and tokenizer
ms.load_model_and_tokenizer(
    model_name="vinai/phobert-base",
    model_type="auto",
    trust_remote_code=True
)

# Print model information
ms.print_model_info()

# Generate text
output = ms.generate_text(
    prompt="Xin chào, tôi là",
    max_length=50,
    temperature=0.7
)
print(output)
```

### 6. Database Integration (Programmatic)

```python
from config.db_config import get_db_config, test_database_setup
from sqlalchemy import text

# Test database connection
test_database_setup()

# Get database instance
db = get_db_config()

# Use database session
with db.get_session() as session:
    result = session.execute(text("SELECT version()"))
    print(f"PostgreSQL version: {result.scalar()}")
```

## Services

### DataManager

Handles dataset loading and management using HuggingFace's `datasets` library.

**Key Methods:**
- `load_data(source, split, cache_dir)` - Load dataset
- `get_dataset_info()` - Get dataset metadata
- `get_split(split_name)` - Retrieve specific split
- `print_dataset_info()` - Display dataset information
- `get_num_examples(split)` - Count examples
- `filter_dataset(filter_fn, split)` - Filter dataset
- `map_dataset(map_fn, split, batched)` - Transform dataset

**Example:**
```python
dm = DataManager()
dm.load_data("squad", split="train")

# Filter examples
filtered = dm.filter_dataset(
    lambda x: len(x['context']) > 100,
    split="train"
)

# Map function to examples
def preprocess(example):
    example['text_length'] = len(example['context'])
    return example

processed = dm.map_dataset(preprocess, batched=False)
```

### ModelService

Manages model and tokenizer loading with support for various model types and quantization.

**Key Methods:**
- `load_model(model_name, model_type, load_in_8bit, load_in_4bit)` - Load model
- `load_tokenizer(tokenizer_name)` - Load tokenizer
- `load_model_and_tokenizer(model_name)` - Load both together
- `get_model_info()` - Get model metadata
- `print_model_info()` - Display model information
- `generate_text(prompt, max_length, temperature)` - Generate text
- `save_model(save_path)` - Save model to disk
- `set_train_mode()` / `set_eval_mode()` - Toggle modes
- `to_device(device)` - Move model to device

**Supported Model Types:**
- `auto` - Auto-detect model architecture
- `causal_lm` - Causal language models (GPT-style)
- `sequence_classification` - Classification models

**Example:**
```python
ms = ModelService(device="cuda")

# Load with 8-bit quantization (saves memory)
ms.load_model(
    "vinai/phobert-large",
    model_type="auto",
    load_in_8bit=True,
    trust_remote_code=True
)

ms.load_tokenizer("vinai/phobert-large")

# Set to training mode
ms.set_train_mode()

# Save fine-tuned model
ms.save_model("./models/phobert-finetuned")
```

### DbConfig

Provides PostgreSQL database connection management with connection pooling.

**Key Methods:**
- `test_connection()` - Test database connectivity
- `get_session()` - Get database session (context manager)
- `create_tables(base)` - Create tables from SQLAlchemy models
- `drop_tables(base)` - Drop all tables
- `execute_raw_sql(sql, params)` - Execute raw SQL
- `get_engine_info()` - Get connection pool status
- `print_config_info()` - Display configuration
- `close()` - Cleanup resources

**Example:**
```python
from config.db_config import DbConfig
from sqlalchemy import text

# Initialize with custom settings
db = DbConfig(
    host="localhost",
    port=5432,
    database="phogpt_training"
)

# Test connection
if db.test_connection():
    print("Connected to database!")

# Use session for queries
with db.get_session() as session:
    # Insert training run
    session.execute(
        text("""
            INSERT INTO training_runs (model_name, status, created_at)
            VALUES (:model, :status, NOW())
        """),
        {"model": "phobert-base", "status": "started"}
    )

# Print pool status
db.print_config_info()
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_HOST` | Database host | `localhost` |
| `DB_PORT` | Database port | `5432` |
| `DB_NAME` | Database name | `phogpt_db` |
| `DB_USER` | Database username | `postgres` |
| `DB_PASSWORD` | Database password | `postgres` |
| `DB_POOL_SIZE` | Connection pool size | `10` |
| `DB_MAX_OVERFLOW` | Max overflow connections | `20` |
| `DB_POOL_TIMEOUT` | Connection timeout (seconds) | `30` |
| `DB_POOL_RECYCLE` | Connection recycle time (seconds) | `3600` |
| `DB_ECHO` | Echo SQL queries | `false` |

## Usage Examples

### Complete Training Pipeline Example

```python
from services.data_manager import DataManager
from services.model_service import ModelService
from config.db_config import get_db_config

# 1. Load dataset
dm = DataManager()
dm.load_data("your-dataset-name")
train_data = dm.get_split("train")

# 2. Initialize model
ms = ModelService()
ms.load_model_and_tokenizer(
    "vinai/phobert-base",
    model_type="causal_lm"
)

# 3. Database for tracking (optional)
db = get_db_config()
with db.get_session() as session:
    # Log training start
    session.execute(
        text("INSERT INTO runs (name, status) VALUES (:n, :s)"),
        {"n": "run-001", "s": "started"}
    )

# 4. Training loop would go here
# ... your training code ...

print("Training pipeline initialized successfully!")
```

### Data Preprocessing Example

```python
from services.data_manager import DataManager

dm = DataManager()
dm.load_data("wikipedia", "20220301.vi")

# Define preprocessing function
def preprocess_text(example):
    # Clean and tokenize
    text = example['text'].lower().strip()
    example['processed_text'] = text
    example['word_count'] = len(text.split())
    return example

# Apply preprocessing
processed_dataset = dm.map_dataset(
    preprocess_text,
    batched=False
)

# Filter short articles
filtered_dataset = dm.filter_dataset(
    lambda x: x['word_count'] > 100
)

print(f"Processed {dm.get_num_examples()} examples")
```

### Model Inference Example

```python
from services.model_service import ModelService

ms = ModelService()
ms.load_model_and_tokenizer("vinai/phobert-base")

# Set to evaluation mode
ms.set_eval_mode()

# Generate multiple sequences
prompts = [
    "Trí tuệ nhân tạo là",
    "Việt Nam có",
    "Ngôn ngữ lập trình"
]

for prompt in prompts:
    output = ms.generate_text(
        prompt=prompt,
        max_length=50,
        temperature=0.8,
        top_p=0.9
    )
    print(f"Prompt: {prompt}")
    print(f"Output: {output}\n")
```

## Development

### Running Tests

```bash
# Test database connection
python -c "from config.db_config import test_database_setup; test_database_setup()"

# Test data loading
python main.py
```

### Code Style

This project follows PEP 8 style guidelines with type hints for better code quality.

### Logging

All services include logging. Set logging level:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Troubleshooting

### Database Connection Issues

If you encounter database connection errors:

1. Ensure PostgreSQL is running
2. Check credentials in `.env` file
3. Verify network connectivity
4. Check firewall settings

```bash
# Test PostgreSQL connection
psql -h localhost -U postgres -d phogpt_db
```

### CUDA/GPU Issues

If models don't use GPU:

```python
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA version: {torch.version.cuda}")
```

### Memory Issues

For large models, use quantization:

```python
ms.load_model(
    "large-model-name",
    load_in_8bit=True,  # or load_in_4bit=True
)
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is part of the PhoGPT training framework.

## Support

For issues and questions:
- Check the documentation above
- Review error logs with `logging.DEBUG` enabled
- Check environment variables configuration

## Acknowledgments

- HuggingFace for the `transformers` and `datasets` libraries
- VinAI for the PhoBERT models
- SQLAlchemy for database ORM
