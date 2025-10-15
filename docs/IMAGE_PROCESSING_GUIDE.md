# Image Processing Guide

## Overview

The enhanced chatbot now supports processing both PDF documents and images to extract text content. This allows users to upload images containing text (such as scanned documents, screenshots, or photos with text) and ask questions about their content.

## Supported Image Formats

- **JPG/JPEG** - Standard JPEG images
- **PNG** - Portable Network Graphics
- **BMP** - Bitmap images
- **GIF** - Graphics Interchange Format
- **TIFF** - Tagged Image File Format
- **WEBP** - WebP format

## Image Processing Methods

### 1. Gemini Vision (Primary)
- Uses Google's Gemini 2.0 Flash model with vision capabilities
- Provides high-quality text extraction with context understanding
- Better at handling complex layouts and mixed content
- Automatically falls back to OCR if Gemini Vision fails

### 2. Tesseract OCR (Fallback)
- Traditional OCR using Tesseract engine
- Supports Vietnamese and English text recognition
- Used as backup when Gemini Vision is unavailable

## API Endpoints

### Upload Document (New)
```
POST /api/chatbot/upload-document
```
- Supports both PDF and image files
- Accepts multipart/form-data with file upload
- Returns processing status and chunk information

### Upload PDF (Legacy)
```
POST /api/chatbot/upload-pdf
```
- Maintained for backward compatibility
- Only accepts PDF files
- Redirects users to use `/upload-document` for images

## Usage Examples

### Using the API

```python
import requests

# Upload an image
with open('document_image.jpg', 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:8000/api/chatbot/upload-document', files=files)
    result = response.json()
    print(result['status'])

# Ask questions about the image content
chat_response = requests.post('http://localhost:8000/api/chatbot/chat', json={
    'query': 'What is the main topic of this document?',
    'chat_history': []
})
answer = chat_response.json()['answer']
print(answer)
```

### Using the Gradio Interface

1. Open the chatbot interface
2. Select "PDF or Image" file type
3. Upload your image file
4. Click "Process & Add to Memory"
5. Wait for processing confirmation
6. Ask questions about the image content

## Best Practices

### Image Quality
- Use high-resolution images (minimum 300 DPI for scanned documents)
- Ensure good contrast between text and background
- Avoid blurry or rotated images
- Use proper lighting when taking photos

### Text Recognition
- Clean, clear text works best
- Avoid handwritten text if possible
- Ensure text is horizontal and not rotated
- Use standard fonts when possible

### File Size
- Recommended maximum file size: 10MB
- Larger files may take longer to process
- Consider compressing images if needed

## Troubleshooting

### Common Issues

1. **"Unsupported file type" error**
   - Ensure your image format is supported
   - Check file extension is correct

2. **Poor text extraction quality**
   - Try improving image quality/resolution
   - Ensure good contrast and lighting
   - Consider using Gemini Vision for better results

3. **"No relevant information found"**
   - The image might not contain readable text
   - Try reprocessing with better image quality
   - Check if the image is too small or blurry

### Error Messages

- `"Error processing document"` - General processing error
- `"Both extraction methods failed"` - Both Gemini and OCR failed
- `"Image file not found"` - File path issue
- `"API key not configured"` - Google API key missing

## Performance Considerations

- **Processing Time**: Images typically take 2-5 seconds to process
- **Memory Usage**: Each image adds chunks to the chatbot's memory
- **API Limits**: Google API has rate limits and usage quotas
- **Storage**: Processed content is stored in memory, not on disk

## Dependencies

The following packages are required for image processing:

```txt
Pillow>=10.0.0
pytesseract>=0.3.10
google-generativeai>=0.7.0
```

Note: Tesseract OCR engine must be installed on the system for OCR functionality.

## Future Enhancements

- Support for handwritten text recognition
- Batch image processing
- Image preprocessing (rotation, noise reduction)
- Multi-language OCR support
- Integration with cloud storage services
