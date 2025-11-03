"""
Test script for semantic caching functionality.
Demonstrates how similar queries can hit the cache.
"""

import sys
import os
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config.cache.redis_cache import RedisCache


def test_semantic_cache():
    """Test semantic caching with similar queries."""
    print("=" * 70)
    print("Semantic Cache Test")
    print("=" * 70)

    # Initialize cache with semantic caching enabled
    cache = RedisCache(
        host='localhost',
        port=6379,
        semantic_similarity_threshold=0.90  # Lower threshold for testing
    )

    if not cache.enabled:
        print("❌ Redis is not available. Please start Redis server.")
        print("   docker-compose up -d redis")
        return

    print(f"\n✓ Redis connected: {cache.host}:{cache.port}")
    print(f"✓ Semantic caching: {'enabled' if cache._semantic_enabled else 'disabled'}")
    print(f"✓ Similarity threshold: {cache.semantic_threshold}")
    print()

    # Clear any existing cache
    cache.invalidate_query_cache()
    print("✓ Cache cleared")
    print()

    # Test data
    test_queries = [
        ("What is Python?", "Original query"),
        ("What's Python?", "Contracted form - should match"),
        ("Tell me about Python", "Different phrasing - should match"),
        ("Python programming language", "Reordered - should match"),
        ("What is JavaScript?", "Different topic - should NOT match"),
    ]

    mock_results = [
        {"id": 1, "content": "Python is a high-level programming language..."},
        {"id": 2, "content": "Created by Guido van Rossum in 1991..."},
    ]

    # Test 1: Cache the first query
    print("=" * 70)
    print("Test 1: Caching Original Query")
    print("=" * 70)
    query1, desc1 = test_queries[0]
    success = cache.set_query_results(query1, mock_results, top_k=5)
    print(f"Query: \"{query1}\"")
    print(f"Cached: {'✓ Success' if success else '❌ Failed'}")
    time.sleep(0.5)  # Give Redis time to store
    print()

    # Test 2: Try to retrieve with exact same query
    print("=" * 70)
    print("Test 2: Exact Match Retrieval")
    print("=" * 70)
    result = cache.get_query_results(query1, top_k=5)
    if result:
        print(f"Query: \"{query1}\"")
        print(f"Result: ✓ Cache HIT (exact match)")
        print(f"Retrieved {len(result)} results")
    else:
        print(f"❌ Cache MISS - unexpected!")
    print()

    # Test 3-5: Try similar queries
    for i in range(1, 4):
        print("=" * 70)
        print(f"Test {i+2}: Semantic Similarity Test")
        print("=" * 70)
        query, desc = test_queries[i]
        print(f"Query: \"{query}\"")
        print(f"Description: {desc}")

        start_time = time.time()
        result = cache.get_query_results(query, top_k=5)
        elapsed = (time.time() - start_time) * 1000

        if result:
            print(f"Result: ✓ Cache HIT (semantic match)")
            print(f"Retrieved {len(result)} results")
            print(f"Time: {elapsed:.2f}ms")
        else:
            print(f"Result: ❌ Cache MISS")
            print(f"Time: {elapsed:.2f}ms")
        print()

    # Test 6: Completely different query
    print("=" * 70)
    print("Test 6: Different Topic (Expected MISS)")
    print("=" * 70)
    query5, desc5 = test_queries[4]
    print(f"Query: \"{query5}\"")
    print(f"Description: {desc5}")

    result = cache.get_query_results(query5, top_k=5)
    if result:
        print(f"Result: ❌ Cache HIT - unexpected!")
    else:
        print(f"Result: ✓ Cache MISS (as expected)")
    print()

    # Show cache statistics
    print("=" * 70)
    print("Cache Statistics")
    print("=" * 70)
    stats = cache.get_cache_stats()
    print(f"Enabled: {stats.get('enabled')}")
    print(f"Status: {stats.get('status')}")
    print(f"Total Keys: {stats.get('total_keys')}")
    print(f"Query Cache Keys: {stats.get('query_cache_keys')}")
    print(f"Embedding Keys: {stats.get('embedding_keys', 0)}")
    print(f"Semantic Cache: {stats.get('semantic_cache_enabled')}")
    print(f"Hit Rate: {stats.get('hit_rate', 0):.1f}%")
    print()

    # Cleanup
    cache.invalidate_query_cache()
    print("✓ Cache cleared after test")


if __name__ == "__main__":
    try:
        test_semantic_cache()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
