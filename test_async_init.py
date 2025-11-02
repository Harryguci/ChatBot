"""
Test script to demonstrate the performance improvement of async initialization.
This script compares synchronous vs async initialization times.
"""

import asyncio
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.chatbot_memory import Chatbot


def test_sync_initialization():
    """Test synchronous initialization (old way)."""
    print("\n" + "="*60)
    print("Testing SYNCHRONOUS initialization")
    print("="*60)

    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        print("Error: GOOGLE_API_KEY not found in environment")
        return None

    start_time = time.time()

    # Synchronous initialization - setup_models and load_documents run sequentially
    chatbot = Chatbot(google_api_key)

    end_time = time.time()
    elapsed = end_time - start_time

    print(f"\n✓ Synchronous initialization completed in {elapsed:.2f} seconds")
    print(f"  - Documents loaded: {len(chatbot.processed_files)}")
    print(f"  - Total chunks: {len(chatbot.documents)}")
    print(f"  - Vintern enabled: {chatbot.vintern_service.is_enabled()}")

    return elapsed


async def test_async_initialization():
    """Test asynchronous initialization (new way)."""
    print("\n" + "="*60)
    print("Testing ASYNCHRONOUS initialization")
    print("="*60)

    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        print("Error: GOOGLE_API_KEY not found in environment")
        return None

    start_time = time.time()

    # Async initialization - setup_models and load_documents run concurrently
    chatbot = await Chatbot.create_async(google_api_key)

    end_time = time.time()
    elapsed = end_time - start_time

    print(f"\n✓ Asynchronous initialization completed in {elapsed:.2f} seconds")
    print(f"  - Documents loaded: {len(chatbot.processed_files)}")
    print(f"  - Total chunks: {len(chatbot.documents)}")
    print(f"  - Vintern enabled: {chatbot.vintern_service.is_enabled()}")

    return elapsed


async def main():
    """Run both tests and compare results."""
    print("\n" + "="*60)
    print("CHATBOT INITIALIZATION PERFORMANCE TEST")
    print("="*60)
    print("\nThis test compares synchronous vs async initialization.")
    print("Async initialization runs setup_models() and load_documents_from_database()")
    print("concurrently, which should be faster.\n")

    # Test synchronous initialization
    sync_time = test_sync_initialization()

    # Wait a bit between tests
    await asyncio.sleep(2)

    # Test asynchronous initialization
    async_time = await test_async_initialization()

    # Compare results
    if sync_time and async_time:
        print("\n" + "="*60)
        print("PERFORMANCE COMPARISON")
        print("="*60)
        print(f"Synchronous:  {sync_time:.2f} seconds")
        print(f"Asynchronous: {async_time:.2f} seconds")

        improvement = sync_time - async_time
        improvement_pct = (improvement / sync_time) * 100

        print(f"\nTime saved:   {improvement:.2f} seconds ({improvement_pct:.1f}% faster)")

        if improvement > 0:
            print("\n✓ Async initialization is FASTER! 🚀")
        elif improvement < 0:
            print("\n⚠ Async initialization was slower (unexpected)")
        else:
            print("\n≈ Both methods took similar time")

    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
