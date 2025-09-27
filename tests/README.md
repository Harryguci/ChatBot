# Chatbot Unit Tests

This directory contains comprehensive unit tests for the Chatbot API and PDFChatbot functionality.

## Test Structure

- `conftest.py` - Pytest fixtures and configuration
- `test_chatbot_api.py` - Tests for FastAPI endpoints
- `test_chatbot_memory.py` - Tests for PDFChatbot class functionality
- `pytest.ini` - Pytest configuration
- `requirements-test.txt` - Test dependencies

## Running Tests

### 1. Install Test Dependencies

```bash
# Install test requirements
pip install -r tests/requirements-test.txt

# Or install pytest directly
pip install pytest pytest-asyncio pytest-mock httpx pytest-cov
```

### 2. Run All Tests

```bash
# Run all tests from project root
pytest tests/

# Or run from tests directory
cd tests
pytest
```

### 3. Run Specific Test Files

```bash
# Test only API endpoints
pytest tests/test_chatbot_api.py

# Test only PDFChatbot class
pytest tests/test_chatbot_memory.py

# Test specific test class
pytest tests/test_chatbot_api.py::TestChatbotAPI

# Test specific test method
pytest tests/test_chatbot_api.py::TestChatbotAPI::test_health_check_healthy
```

### 4. Run with Coverage

```bash
# Run tests with coverage report
pytest tests/ --cov=src --cov-report=html --cov-report=term

# View HTML coverage report
open htmlcov/index.html  # On macOS/Linux
# or open htmlcov/index.html in browser on Windows
```

### 5. Run with Verbose Output

```bash
# Verbose output showing test names
pytest tests/ -v

# Extra verbose with print statements
pytest tests/ -s -v
```

### 6. Run Specific Test Categories

```bash
# Run only unit tests (if marked)
pytest tests/ -m unit

# Run only integration tests (if marked)
pytest tests/ -m integration

# Skip slow tests
pytest tests/ -m "not slow"
```

## Test Configuration

The tests use the following configuration:

- **Mocking**: All external dependencies (Google API, SentenceTransformer) are mocked
- **Environment**: Tests run with `GOOGLE_API_KEY=test_api_key`
- **Fixtures**: Reusable test data and mock objects
- **Isolation**: Each test is independent and cleans up after itself

## Environment Variables

Tests automatically set required environment variables:
- `GOOGLE_API_KEY=test_api_key` (mocked)

## Test Examples

### API Endpoint Tests
- Health check endpoint
- PDF upload and processing
- Chat functionality
- Memory management
- Error handling

### PDFChatbot Class Tests
- Initialization
- PDF text extraction
- Document chunking
- Embedding creation
- Document search
- Answer generation
- Memory management

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure you're running from the project root
2. **Missing Dependencies**: Install test requirements with `pip install -r tests/requirements-test.txt`
3. **Path Issues**: Tests automatically add `src/` to Python path

### Debug Mode

```bash
# Run single test with debugging
pytest tests/test_chatbot_api.py::TestChatbotAPI::test_health_check_healthy -v -s

# Run with pdb debugger on failures
pytest tests/ --pdb
```

## Continuous Integration

For CI/CD pipelines, use:

```bash
# Run tests with coverage and fail on coverage threshold
pytest tests/ --cov=src --cov-fail-under=80 --cov-report=xml
```
