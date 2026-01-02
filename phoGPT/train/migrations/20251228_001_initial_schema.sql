-- Migration: Initial schema for training management
-- Created: 2025-12-28
-- Description: Creates training_runs and training_metrics tables

-- Table: training_runs
-- Stores information about each training run
CREATE TABLE IF NOT EXISTS training_runs (
    id SERIAL PRIMARY KEY,
    run_name VARCHAR(255) NOT NULL UNIQUE,
    model_name VARCHAR(255) NOT NULL,
    dataset_name VARCHAR(255) NOT NULL,

    -- Status tracking
    status VARCHAR(50) NOT NULL DEFAULT 'pending',

    -- Hyperparameters (stored as JSON)
    hyperparameters JSON,

    -- Key hyperparameters (duplicated for easy querying)
    learning_rate FLOAT,
    batch_size INTEGER,
    num_epochs INTEGER,
    max_steps INTEGER,

    -- Progress tracking
    current_epoch INTEGER DEFAULT 0,
    current_step INTEGER DEFAULT 0,
    progress_percentage FLOAT DEFAULT 0.0,

    -- Metrics
    train_loss FLOAT,
    eval_loss FLOAT,
    best_metric FLOAT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    updated_at TIMESTAMP,

    -- Output and notes
    output_dir TEXT,
    error_message TEXT,
    notes TEXT
);

-- Create index on run_name for faster lookups
CREATE INDEX IF NOT EXISTS idx_training_runs_run_name ON training_runs(run_name);

-- Create index on status for filtering
CREATE INDEX IF NOT EXISTS idx_training_runs_status ON training_runs(status);

-- Create index on created_at for sorting
CREATE INDEX IF NOT EXISTS idx_training_runs_created_at ON training_runs(created_at DESC);


-- Table: training_metrics
-- Stores step-by-step metrics for each training run
CREATE TABLE IF NOT EXISTS training_metrics (
    id SERIAL PRIMARY KEY,
    training_run_id INTEGER NOT NULL REFERENCES training_runs(id) ON DELETE CASCADE,

    -- Step and epoch
    step INTEGER NOT NULL,
    epoch INTEGER,

    -- Metrics
    loss FLOAT,
    eval_loss FLOAT,
    learning_rate FLOAT,
    gradient_norm FLOAT,

    -- Additional metrics (stored as JSON)
    metrics JSON,

    -- Timestamp
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Unique constraint: one metric per step per training run
    UNIQUE(training_run_id, step)
);

-- Create index on training_run_id for faster joins
CREATE INDEX IF NOT EXISTS idx_training_metrics_run_id ON training_metrics(training_run_id);

-- Create index on step for sorting
CREATE INDEX IF NOT EXISTS idx_training_metrics_step ON training_metrics(step);

-- Create composite index for common queries
CREATE INDEX IF NOT EXISTS idx_training_metrics_run_step ON training_metrics(training_run_id, step DESC);


-- Comments for documentation
COMMENT ON TABLE training_runs IS 'Stores information about training runs';
COMMENT ON TABLE training_metrics IS 'Stores step-by-step metrics for training runs';

COMMENT ON COLUMN training_runs.status IS 'Current status: pending, running, completed, failed, cancelled';
COMMENT ON COLUMN training_runs.hyperparameters IS 'Full hyperparameters configuration as JSON';
COMMENT ON COLUMN training_runs.progress_percentage IS 'Training progress from 0 to 100';

COMMENT ON COLUMN training_metrics.metrics IS 'Additional custom metrics as JSON';
