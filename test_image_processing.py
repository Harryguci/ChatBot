#!/usr/bin/env python3
"""
Test script to verify image processing functionality
"""
import os
import sys
import tempfile
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

# Add src to path
sys.path.append('src')

def create_test_image():
    """Create a simple test image with text"""
    # Create a white image
    img = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img)
    
    # Try to use a default font, fallback to basic if not available
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except:
        font = ImageFont.load_default()
    
    # Add some text
    text_lines = [
        "TEST DOCUMENT",
        "This is a test image with text content.",
        "The chatbot should be able to extract this text.",
        "Line 4: More test content here.",
        "Line 5: Final test line."
    ]
    
    y_position = 50
    for line in text_lines:
        draw.text((50, y_position), line, fill='black', font=font)
        y_position += 60
    
    return img

def test_image_processing():
    """Test the image processing functionality"""
    print("Testing image processing functionality...")
    
    # Create a test image
    test_img = create_test_image()
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
        test_img.save(tmp_file.name)
        image_path = tmp_file.name
    
    try:
        # Import the chatbot class
        from chatbot_memory import PDFChatbot
        
        # Check if API key is available
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("❌ GOOGLE_API_KEY not found. Please set it in your environment.")
            return False
        
        # Initialize chatbot
        print("Initializing chatbot...")
        chatbot = PDFChatbot(api_key)
        
        # Test image file detection
        print("Testing image file detection...")
        is_image = chatbot.is_image_file(image_path)
        print(f"✓ Image file detection: {is_image}")
        
        # Test image processing
        print("Processing test image...")
        status, processed_files = chatbot.process_document(image_path)
        print(f"✓ Processing result: {status}")
        print(f"✓ Processed files: {processed_files}")
        
        # Test if document was added to memory
        print(f"✓ Total documents in memory: {len(chatbot.documents)}")
        print(f"✓ Total chunks: {len(chatbot.documents)}")
        
        # Test search functionality
        print("Testing search functionality...")
        results = chatbot.search_relevant_documents("test content", top_k=3)
        print(f"✓ Search results: {len(results)} documents found")
        
        if results:
            print(f"✓ First result similarity: {results[0][1]:.3f}")
            print(f"✓ First result preview: {results[0][2]['preview'][:100]}...")
        
        print("✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False
    
    finally:
        # Clean up
        if os.path.exists(image_path):
            os.unlink(image_path)

if __name__ == "__main__":
    success = test_image_processing()
    sys.exit(0 if success else 1)
