"""
Quick test script for the Training API.
Demonstrates creating, starting, and monitoring a training run.
"""

import requests
import time
import json

BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/train"


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_json(data):
    """Pretty print JSON data."""
    print(json.dumps(data, indent=2))


def test_health_check():
    """Test the health check endpoint."""
    print_section("Health Check")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status Code: {response.status_code}")
    print_json(response.json())
    return response.status_code == 200


def test_create_training_run():
    """Create a new training run."""
    print_section("Create Training Run")

    payload = {
        "run_name": f"test-run-{int(time.time())}",
        "model_name": "vinai/phobert-base",
        "dataset_name": "squad_v2",
        "hyperparameters": {
            "learning_rate": 5e-5,
            "batch_size": 8,
            "num_epochs": 3,
            "warmup_steps": 500,
            "fp16": True,
            "save_steps": 500,
            "eval_steps": 500,
        },
        "notes": "Test run created by test_api.py script"
    }

    print("Request payload:")
    print_json(payload)

    response = requests.post(f"{API_BASE}/runs", json=payload)

    print(f"\nStatus Code: {response.status_code}")

    if response.status_code == 201:
        data = response.json()
        print("\nCreated training run:")
        print_json(data)
        return data["id"]
    else:
        print(f"Error: {response.text}")
        return None


def test_list_training_runs():
    """List all training runs."""
    print_section("List Training Runs")

    response = requests.get(f"{API_BASE}/runs", params={"limit": 5})

    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        runs = response.json()
        print(f"\nFound {len(runs)} training run(s):")
        for run in runs:
            print(f"  - ID: {run['id']}, Name: {run['run_name']}, Status: {run['status']}")
        return True
    else:
        print(f"Error: {response.text}")
        return False


def test_get_training_run(run_id):
    """Get detailed information about a training run."""
    print_section(f"Get Training Run {run_id}")

    response = requests.get(f"{API_BASE}/runs/{run_id}")

    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print("\nTraining run details:")
        print_json(data)
        return True
    else:
        print(f"Error: {response.text}")
        return False


def test_start_training(run_id):
    """Start a training run."""
    print_section(f"Start Training Run {run_id}")

    response = requests.post(
        f"{API_BASE}/runs/{run_id}/start",
        params={"dataset_split": "train"}
    )

    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print("\nTraining started:")
        print_json(data)
        return True
    else:
        print(f"Error: {response.text}")
        return False


def test_get_status(run_id):
    """Get current status of a training run."""
    print_section(f"Get Training Status {run_id}")

    response = requests.get(f"{API_BASE}/runs/{run_id}/status")

    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print("\nCurrent status:")
        print_json(data)
        return True
    else:
        print(f"Error: {response.text}")
        return False


def test_log_metric(run_id, step, loss):
    """Log a training metric."""
    print_section(f"Log Metric for Run {run_id}")

    response = requests.post(
        f"{API_BASE}/runs/{run_id}/log-metric",
        params={
            "step": step,
            "epoch": step // 100,
            "loss": loss,
            "learning_rate": 5e-5,
        }
    )

    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"\nLogged metric at step {step}")
        print_json(data)
        return True
    else:
        print(f"Error: {response.text}")
        return False


def test_get_metrics(run_id):
    """Get training metrics."""
    print_section(f"Get Metrics for Run {run_id}")

    response = requests.get(
        f"{API_BASE}/runs/{run_id}/metrics",
        params={"limit": 5}
    )

    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        metrics = response.json()
        print(f"\nFound {len(metrics)} metric(s):")
        for metric in metrics:
            print(f"  - Step: {metric['step']}, Loss: {metric.get('loss', 'N/A')}")
        return True
    else:
        print(f"Error: {response.text}")
        return False


def test_update_status(run_id, status):
    """Update training status."""
    print_section(f"Update Status for Run {run_id}")

    payload = {
        "status": status,
        "error_message": None
    }

    response = requests.patch(
        f"{API_BASE}/runs/{run_id}/status",
        json=payload
    )

    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"\nStatus updated to: {status}")
        print_json(data)
        return True
    else:
        print(f"Error: {response.text}")
        return False


def run_complete_test():
    """Run a complete test workflow."""
    print("\n" + "🚀" * 30)
    print("  PHOGPT TRAINING API - COMPLETE TEST")
    print("🚀" * 30)

    # 1. Health check
    if not test_health_check():
        print("\n❌ Health check failed. Is the server running?")
        return

    # 2. List existing runs
    test_list_training_runs()

    # 3. Create new run
    run_id = test_create_training_run()
    if not run_id:
        print("\n❌ Failed to create training run")
        return

    # 4. Get run details
    test_get_training_run(run_id)

    # 5. Start training
    print("\nNote: Starting training will attempt to load model and dataset.")
    print("This may fail if you don't have the models/datasets available.")
    proceed = input("Proceed with starting training? (y/n): ")

    if proceed.lower() == 'y':
        test_start_training(run_id)

    # 6. Get status
    test_get_status(run_id)

    # 7. Log some metrics
    print("\nSimulating metric logging...")
    for step in [100, 200, 300]:
        test_log_metric(run_id, step, 1.5 - (step * 0.001))
        time.sleep(0.5)

    # 8. Get logged metrics
    test_get_metrics(run_id)

    # 9. Update status to completed
    test_update_status(run_id, "completed")

    # 10. Final status check
    test_get_status(run_id)

    print("\n" + "✅" * 30)
    print("  TEST COMPLETED SUCCESSFULLY!")
    print("✅" * 30)
    print(f"\nTraining Run ID: {run_id}")
    print(f"View in browser: {BASE_URL}/docs")


if __name__ == "__main__":
    try:
        run_complete_test()
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to API server")
        print(f"Make sure the server is running at {BASE_URL}")
        print("\nStart the server with: python app.py")
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
