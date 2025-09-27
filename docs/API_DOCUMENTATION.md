# PDF Chatbot API Documentation

This document describes the REST API endpoints for the PDF Chatbot service, which enables intelligent document-based conversations using Google's Gemini AI model and advanced text processing techniques.

## Base URL
```
http://localhost:8000/api/chatbot
```

## Authentication
The API requires a Google API key to be set as an environment variable:
```bash
export GOOGLE_API_KEY="your_google_api_key_here"
```

## Technical Overview

The chatbot uses several advanced technologies:
- **AI Model**: Google Gemini 1.5 Flash for generating responses
- **Embeddings**: SentenceTransformer (paraphrase-multilingual-MiniLM-L12-v2) for semantic search
- **Text Processing**: Advanced chunking strategy that preserves document structure
- **Memory Management**: Persistent storage of processed documents across multiple uploads

## Data Models

### ChatRequest
```json
{
  "query": "string (required)",
  "chat_history": "array of tuples (optional, default: [])"
}
```

### ChatResponse
```json
{
  "answer": "string",
  "chat_history": "array of tuples",
  "confidence": "float (0.0-1.0, optional)"
}
```

### ProcessPDFResponse
```json
{
  "status": "string",
  "processed_files": "string (markdown formatted)",
  "total_chunks": "integer (optional)"
}
```

### MemoryStatus
```json
{
  "processed_files": "array of strings",
  "total_chunks": "integer",
  "total_documents": "integer"
}
```

## Endpoints

### 1. Health Check
**GET** `/health`

Check if the chatbot service is running and healthy. This endpoint will attempt to initialize the chatbot if it hasn't been created yet.

**Response:**
```json
{
  "status": "healthy",
  "service": "chatbot-api"
}
```

**Error Response (503):**
```json
{
  "status": "unhealthy",
  "reason": "Google API key not configured"
}
```

### 2. Upload and Process PDF
**POST** `/upload-pdf`

Upload a PDF file and process it using advanced chunking strategies. The system automatically:
- Extracts text from PDF pages
- Cleans and normalizes text
- Applies intelligent chunking (max 1000 chars per chunk with 100 char overlap)
- Creates semantic embeddings for search
- Preserves document structure and headings

**Request:**
- Content-Type: `multipart/form-data`
- Body: PDF file (only .pdf files supported)

**Success Response:**
```json
{
  "status": "Xử lý thành công 'filename.pdf'!\n- Số chunks mới: 25\n- Tổng số chunks trong bộ nhớ: 25",
  "processed_files": "**Các tài liệu trong bộ nhớ:**\n1. filename.pdf",
  "total_chunks": 25
}
```

**Error Responses:**
- `400`: Only PDF files are supported
- `500`: Error processing PDF

**Behavior:**
- Duplicate files are automatically detected and skipped
- Multiple PDFs can be uploaded to build a comprehensive knowledge base
- Each chunk includes metadata (source file, heading, length, preview)

### 3. Chat with Documents
**POST** `/chat`

Ask questions about uploaded documents. The system performs semantic search to find relevant content and generates contextual answers.

**Request:**
```json
{
  "query": "What is this document about?",
  "chat_history": []
}
```

**Response:**
```json
{
  "answer": "Based on the document, this appears to be about...\n\n---\n*Độ tin cậy của nguồn chính: 85%* (Cao)",
  "chat_history": [
    ["What is this document about?", "Based on the document, this appears to be about..."]
  ],
  "confidence": 0.85
}
```

**Behavior:**
- Searches top 5 most relevant document chunks
- Requires minimum similarity threshold of 0.3
- Includes source file references in answers
- Provides confidence scores with qualitative labels:
  - < 0.4: Low (may not be closely related)
  - 0.4-0.65: Medium
  - > 0.65: High
- Maintains conversation history across requests

**Error Responses:**
- `400`: Query cannot be empty
- `500`: Failed to generate answer

### 4. Get Memory Status
**GET** `/memory/status`

Get comprehensive information about the chatbot's current memory state.

**Response:**
```json
{
  "processed_files": ["document1.pdf", "document2.pdf"],
  "total_chunks": 50,
  "total_documents": 50
}
```

**Fields:**
- `processed_files`: List of successfully processed PDF filenames
- `total_chunks`: Total number of text chunks in memory
- `total_documents`: Total number of document metadata entries

### 5. Clear Memory
**DELETE** `/memory`

Clear all uploaded documents, embeddings, and chat history from the chatbot's memory. This resets the chatbot to its initial state.

**Response:**
```json
{
  "message": "Memory cleared successfully",
  "status": "success"
}
```

**Behavior:**
- Removes all processed files from memory
- Clears document embeddings
- Resets document metadata
- Maintains chatbot instance for future uploads

## Error Responses

All endpoints may return error responses in the following format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

Common HTTP status codes:
- `400` - Bad Request (invalid input, empty query, non-PDF files)
- `500` - Internal Server Error (processing error, model initialization failure)
- `503` - Service Unavailable (API key not configured)

## Usage Examples

### Complete Workflow Example

Here's a complete example showing how to use the API for document analysis:

```python
import requests
import json

base_url = "http://localhost:8000/api/chatbot"

# 1. Check service health
health_response = requests.get(f"{base_url}/health")
print("Health check:", health_response.json())

# 2. Upload multiple PDFs
pdf_files = ["document1.pdf", "document2.pdf", "document3.pdf"]
for pdf_file in pdf_files:
    with open(pdf_file, 'rb') as f:
        files = {'file': f}
        response = requests.post(f"{base_url}/upload-pdf", files=files)
        print(f"Uploaded {pdf_file}:", response.json())

# 3. Check memory status
status_response = requests.get(f"{base_url}/memory/status")
print("Memory status:", status_response.json())

# 4. Start a conversation
chat_history = []
questions = [
    "What are the main topics covered in these documents?",
    "Can you summarize the key findings?",
    "What recommendations are mentioned?"
]

for question in questions:
    payload = {
        "query": question,
        "chat_history": chat_history
    }
    response = requests.post(f"{base_url}/chat", json=payload)
    result = response.json()
    
    print(f"\nQ: {question}")
    print(f"A: {result['answer']}")
    print(f"Confidence: {result['confidence']:.2%}")
    
    # Update chat history for context
    chat_history = result['chat_history']
```

### Using curl

1. **Health Check:**
```bash
curl -X GET http://localhost:8000/api/chatbot/health
```

2. **Upload PDF:**
```bash
curl -X POST \
  -F "file=@document.pdf" \
  http://localhost:8000/api/chatbot/upload-pdf
```

3. **Ask Question with Context:**
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main conclusions?", 
    "chat_history": [
      ["What is this document about?", "This document discusses..."],
      ["What methodology was used?", "The study used a quantitative approach..."]
    ]
  }' \
  http://localhost:8000/api/chatbot/chat
```

4. **Get Memory Status:**
```bash
curl -X GET http://localhost:8000/api/chatbot/memory/status
```

5. **Clear Memory:**
```bash
curl -X DELETE http://localhost:8000/api/chatbot/memory
```

### Error Handling Example

```python
import requests

def safe_api_call(url, method="GET", **kwargs):
    try:
        if method.upper() == "GET":
            response = requests.get(url, **kwargs)
        elif method.upper() == "POST":
            response = requests.post(url, **kwargs)
        elif method.upper() == "DELETE":
            response = requests.delete(url, **kwargs)
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 400:
            print("Bad request - check your input data")
        elif e.response.status_code == 500:
            print("Server error - check logs")
        elif e.response.status_code == 503:
            print("Service unavailable - check API key configuration")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None

# Usage
result = safe_api_call("http://localhost:8000/api/chatbot/health")
if result:
    print("Service is healthy:", result)
```

## Getting Started

1. **Set up environment:**
```bash
export GOOGLE_API_KEY="your_google_api_key_here"
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Start the server:**
```bash
cd src
python main.py
```

4. **Test the API:**
```bash
# Test health endpoint
curl http://localhost:8000/api/chatbot/health

# Upload a PDF
curl -X POST -F "file=@your_document.pdf" http://localhost:8000/api/chatbot/upload-pdf

# Ask a question
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"query": "What is this document about?", "chat_history": []}' \
  http://localhost:8000/api/chatbot/chat
```

## Important Limitations and Constraints

### File Processing
- **File Size**: Large PDFs may take longer to process; consider file size limits
- **Text Extraction**: Only text-based PDFs are supported; scanned/image PDFs may not work
- **Language Support**: Optimized for multilingual content but best results with Vietnamese and English
- **Duplicate Detection**: Files with identical names are automatically skipped

### Memory Management
- **Memory Persistence**: All data is stored in memory and will be lost on server restart
- **Chunk Limits**: Maximum 1000 characters per chunk with 100 character overlap
- **Embedding Storage**: All embeddings are kept in memory; consider memory usage for large document sets

### AI Responses
- **Confidence Threshold**: Responses with similarity < 0.3 are rejected
- **Context Window**: Limited to top 5 most relevant chunks per query
- **Source Attribution**: Answers include source file references when possible
- **Language**: Responses are primarily in Vietnamese with English support

### Performance Considerations
- **Concurrent Requests**: Single chatbot instance handles all requests sequentially
- **Processing Time**: PDF processing time depends on document size and complexity
- **API Rate Limits**: Subject to Google Gemini API rate limits
- **Memory Usage**: Embeddings and documents consume significant RAM

### Security Notes
- **API Key**: Google API key must be kept secure and not exposed in client-side code
- **File Upload**: Only PDF files are accepted; other file types are rejected
- **Temporary Files**: Uploaded files are temporarily stored and automatically cleaned up
