"""
Test script to verify the embeddings loading fix.
Run this after the fix to ensure embeddings are loaded correctly.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set logging level to DEBUG to see detailed logs
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from src.chatbot_memory import Chatbot
from src.config.db.services import document_service, document_chunk_service


def test_embeddings_loading():
    """Test that embeddings are properly loaded from database."""

    print("\n" + "="*70)
    print("TESTING EMBEDDINGS LOADING FIX")
    print("="*70 + "\n")

    # Step 1: Check database state
    print("-" * 70)
    print("STEP 1: Checking Database")
    print("-" * 70)

    documents = document_service.get_all_processed_documents()
    print(f"Documents in database: {len(documents)}")

    total_chunks = 0
    chunks_with_embeddings = 0

    for doc in documents:
        chunks = document_chunk_service.get_chunks_by_document(doc.id)
        total_chunks += len(chunks)

        for chunk in chunks:
            if chunk.embedding is not None:
                chunks_with_embeddings += 1

    print(f"Total chunks: {total_chunks}")
    print(f"Chunks with embeddings: {chunks_with_embeddings}")

    if chunks_with_embeddings == 0:
        print("\n❌ ERROR: No embeddings in database!")
        print("   You need to re-process documents to generate embeddings.")
        return False

    print(f"✓ Database has {chunks_with_embeddings} embeddings\n")

    # Step 2: Initialize Chatbot (synchronous)
    print("-" * 70)
    print("STEP 2: Initializing Chatbot (Synchronous)")
    print("-" * 70)

    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        print("❌ ERROR: GOOGLE_API_KEY not found in environment")
        return False

    try:
        chatbot = Chatbot(google_api_key)
        print("✓ Chatbot initialized successfully\n")
    except Exception as e:
        print(f"❌ ERROR: Failed to initialize chatbot: {str(e)}")
        return False

    # Step 3: Check if embeddings were loaded
    print("-" * 70)
    print("STEP 3: Verifying Embeddings Loaded")
    print("-" * 70)

    print(f"Documents loaded: {len(chatbot.documents)}")
    print(f"Metadata entries: {len(chatbot.document_metadata)}")
    print(f"Processed files: {len(chatbot.processed_files)}")

    if chatbot.embeddings is None:
        print(f"\n❌ FAILED: Chatbot.embeddings is None!")
        print("   Expected: numpy array")
        print("   Actual: None")
        return False

    if len(chatbot.embeddings) == 0:
        print(f"\n❌ FAILED: Chatbot.embeddings is empty!")
        print("   Expected: at least one embedding")
        print("   Actual: 0 embeddings")
        return False

    print(f"✓ Embeddings loaded: {len(chatbot.embeddings)} vectors")
    print(f"  Shape: {chatbot.embeddings.shape}")
    print(f"  Dtype: {chatbot.embeddings.dtype}")

    # Check if counts match
    if len(chatbot.embeddings) != len(chatbot.documents):
        print(f"\n⚠ WARNING: Mismatch between embeddings and documents")
        print(f"  Embeddings: {len(chatbot.embeddings)}")
        print(f"  Documents: {len(chatbot.documents)}")
    else:
        print(f"✓ Counts match: {len(chatbot.embeddings)} embeddings for {len(chatbot.documents)} documents")

    # Step 4: Test search functionality
    print("\n" + "-" * 70)
    print("STEP 4: Testing Search Functionality")
    print("-" * 70)

    if len(chatbot.documents) > 0:
        # Get a sample text from the first document
        sample_query = chatbot.documents[0][:50] if len(chatbot.documents[0]) > 50 else chatbot.documents[0]
        print(f"Testing with query: '{sample_query}...'")

        try:
            results = chatbot.search_relevant_documents(sample_query, top_k=3)
            print(f"✓ Search returned {len(results)} results")

            for i, (doc, score, metadata) in enumerate(results, 1):
                print(f"  Result {i}: score={score:.4f}, source={metadata.get('source_file', 'unknown')}")

        except Exception as e:
            print(f"❌ ERROR: Search failed: {str(e)}")
            return False
    else:
        print("⚠ Skipping search test (no documents loaded)")

    # Step 5: Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    success = (
        chatbot.embeddings is not None and
        len(chatbot.embeddings) > 0 and
        len(chatbot.embeddings) == len(chatbot.documents)
    )

    if success:
        print("✅ ALL TESTS PASSED!")
        print("\nEmbeddings are now loading correctly from the database.")
        print("The chatbot should work properly for text-based searches.")
    else:
        print("❌ SOME TESTS FAILED")
        print("\nPlease review the errors above and:")
        print("  1. Check if embeddings exist in database (run diagnose_embeddings.py)")
        print("  2. Verify database connection is working")
        print("  3. Check the logs for detailed error messages")

    print("\n" + "="*70 + "\n")

    return success


if __name__ == "__main__":
    success = test_embeddings_loading()
    sys.exit(0 if success else 1)
