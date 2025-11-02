"""
Diagnostic script to check if embeddings exist in the database
and identify why they might not be loading into Chatbot.embeddings
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.config.db.services import document_service, document_chunk_service
from src.config.db.db_connection import get_database_connection


def diagnose_database_embeddings():
    """Check database for embeddings and diagnose loading issues."""

    print("="*70)
    print("EMBEDDING DIAGNOSTICS")
    print("="*70)

    # Initialize database
    try:
        db = get_database_connection()
        if not db.test_connection():
            print("❌ Database connection failed!")
            return
        print("✓ Database connection successful\n")
    except Exception as e:
        print(f"❌ Database error: {str(e)}")
        return

    # Get all documents
    print("-" * 70)
    print("CHECKING DOCUMENTS")
    print("-" * 70)

    documents = document_service.get_all_processed_documents()

    if not documents:
        print("❌ No documents found in database")
        return

    print(f"✓ Found {len(documents)} document(s) in database\n")

    # Check each document's chunks
    total_chunks = 0
    chunks_with_embeddings = 0
    chunks_without_embeddings = 0

    for doc in documents:
        print(f"\nDocument: {doc.filename} (ID: {doc.id})")
        print(f"  Type: {doc.file_type}")
        print(f"  Status: {doc.processing_status}")

        # Get chunks
        chunks = document_chunk_service.get_chunks_by_document(doc.id)

        if not chunks:
            print(f"  ⚠ No chunks found")
            continue

        print(f"  Chunks: {len(chunks)}")
        total_chunks += len(chunks)

        # Check each chunk for embeddings
        for i, chunk in enumerate(chunks):
            has_embedding = chunk.embedding is not None
            embedding_size = len(chunk.embedding) if has_embedding else 0

            if has_embedding:
                chunks_with_embeddings += 1
                print(f"    Chunk {i}: ✓ Has embedding (size: {embedding_size})")
            else:
                chunks_without_embeddings += 1
                print(f"    Chunk {i}: ❌ No embedding")

            # Check embedding type
            if has_embedding:
                emb_type = type(chunk.embedding).__name__
                print(f"       Type: {emb_type}")

                # Try to inspect the embedding
                try:
                    if hasattr(chunk.embedding, '__iter__'):
                        # Check if it's iterable
                        first_val = chunk.embedding[0] if len(chunk.embedding) > 0 else None
                        print(f"       First value: {first_val}")
                except Exception as e:
                    print(f"       ⚠ Error inspecting embedding: {str(e)}")

            # Check Vintern embedding
            if chunk.vintern_embedding is not None:
                vintern_size = len(chunk.vintern_embedding)
                print(f"       Vintern: ✓ (size: {vintern_size})")

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Total documents: {len(documents)}")
    print(f"Total chunks: {total_chunks}")
    print(f"Chunks with embeddings: {chunks_with_embeddings}")
    print(f"Chunks without embeddings: {chunks_without_embeddings}")

    if chunks_with_embeddings == 0:
        print("\n❌ PROBLEM: No chunks have embeddings!")
        print("   This explains why Chatbot.embeddings is empty.")
        print("\n   Possible causes:")
        print("   1. Embeddings were not generated during document processing")
        print("   2. Embedding generation failed silently")
        print("   3. Database migration issue")
    elif chunks_without_embeddings > 0:
        print(f"\n⚠ WARNING: {chunks_without_embeddings} chunks are missing embeddings")
    else:
        print("\n✓ All chunks have embeddings")

    # Test loading with the same method as Chatbot
    print("\n" + "="*70)
    print("TESTING LOAD PROCESS (Same as Chatbot)")
    print("="*70)

    import numpy as np
    from src.chatbot_memory import vector_to_numpy

    all_embeddings_list = []

    for doc in documents:
        chunks = document_chunk_service.get_chunks_by_document(doc.id)

        for chunk in chunks:
            if chunk.embedding:
                print(f"\nProcessing chunk {chunk.id} from {doc.filename}")
                print(f"  Embedding exists: {chunk.embedding is not None}")

                try:
                    embedding_array = vector_to_numpy(chunk.embedding)

                    if embedding_array is not None:
                        print(f"  ✓ Converted to numpy: shape={embedding_array.shape}, dtype={embedding_array.dtype}")
                        all_embeddings_list.append(embedding_array)
                    else:
                        print(f"  ❌ vector_to_numpy returned None")

                except Exception as e:
                    print(f"  ❌ Error in vector_to_numpy: {str(e)}")

    print(f"\nFinal embeddings_list length: {len(all_embeddings_list)}")

    if all_embeddings_list:
        try:
            embeddings_matrix = np.array(all_embeddings_list)
            print(f"✓ Successfully created embeddings matrix: {embeddings_matrix.shape}")
        except Exception as e:
            print(f"❌ Error creating numpy array: {str(e)}")
    else:
        print("❌ No embeddings collected - THIS IS THE PROBLEM!")

    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    diagnose_database_embeddings()
