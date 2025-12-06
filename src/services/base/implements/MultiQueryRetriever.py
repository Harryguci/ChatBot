"""
Multi-Query Retriever for Enhanced RAG.

This module implements a multi-query retrieval strategy that generates
multiple query variations to improve retrieval coverage and accuracy.

Based on the LangChain MultiQueryRetriever pattern but adapted for
the database-first architecture.
"""

import logging
from typing import List, Set, Callable, Any
import google.generativeai as genai

from src.config.rag_config import get_config

logger = logging.getLogger(__name__)


class MultiQueryRetriever:
    """
    Multi-query retrieval strategy for improved search coverage.

    This retriever generates multiple variations of a user query and
    searches with each variation, then combines and deduplicates results.

    Features:
    - LLM-powered query variation generation
    - Configurable number of variations
    - Result deduplication by chunk ID
    - Score aggregation strategies
    """

    def __init__(
        self,
        llm_model: Any,
        num_variations: int = 3,
        aggregation_strategy: str = 'max'
    ):
        """
        Initialize the multi-query retriever.

        Args:
            llm_model: Gemini GenerativeModel instance for query generation
            num_variations: Number of query variations to generate
            aggregation_strategy: How to combine scores - 'max', 'average', or 'weighted'
        """
        self.llm_model = llm_model
        self.config = get_config()

        # Use config value if available
        self.num_variations = (
            self.config.num_query_variations
            if self.config.multi_query_enabled
            else num_variations
        )

        self.aggregation_strategy = aggregation_strategy

        logger.info(
            f"MultiQueryRetriever initialized: "
            f"{self.num_variations} variations, "
            f"aggregation={aggregation_strategy}"
        )

    def generate_query_variations(self, query: str) -> List[str]:
        """
        Generate query variations using the LLM.

        Args:
            query: Original user query

        Returns:
            List of query variations (including original)
        """
        if not self.config.multi_query_enabled:
            logger.debug("MultiQuery disabled, returning original query only")
            return [query]

        try:
            prompt = f"""You are a helpful AI assistant. Your task is to generate {self.num_variations} different versions of the given question to help retrieve relevant documents from a vector database.

By generating multiple perspectives on the user question, your goal is to help overcome some of the limitations of distance-based similarity search.

Provide these alternative questions separated by newlines. Make sure each variation:
1. Asks for the same information but uses different words
2. Maintains the same intent and context
3. Uses different phrasings and sentence structures
4. Is clear and specific

Original question: {query}

Alternative questions:"""

            response = self.llm_model.generate_content(prompt)
            variations_text = response.text.strip()

            # Parse variations (one per line)
            variations = [
                line.strip()
                for line in variations_text.split('\n')
                if line.strip() and not line.strip().startswith(('1.', '2.', '3.', '4.', '5.', '-', '*'))
            ]

            # Remove numbering if present
            clean_variations = []
            for var in variations:
                # Remove leading numbers like "1. ", "2. ", etc.
                cleaned = var
                for i in range(1, 10):
                    if cleaned.startswith(f"{i}. "):
                        cleaned = cleaned[3:]
                        break
                    if cleaned.startswith(f"{i}) "):
                        cleaned = cleaned[3:]
                        break
                if cleaned:
                    clean_variations.append(cleaned)

            # Limit to requested number
            query_variations = clean_variations[:self.num_variations]

            # Always include original query first
            all_queries = [query] + query_variations

            logger.info(f"Generated {len(query_variations)} query variations")
            logger.debug(f"Variations: {query_variations}")

            return all_queries

        except Exception as e:
            logger.warning(f"Query variation generation failed: {str(e)}")
            logger.warning("Falling back to original query only")
            return [query]

    def retrieve_with_multi_query(
        self,
        query: str,
        search_function: Callable[[str, int], List[tuple]],
        top_k: int = 5
    ) -> List[tuple]:
        """
        Retrieve documents using multi-query strategy.

        Args:
            query: Original user query
            search_function: Function to search for documents
                             Should accept (query_str, top_k) and return
                             List[(content, score, metadata)]
            top_k: Number of final results to return

        Returns:
            List of (content, score, metadata) tuples, deduplicated and ranked
        """
        # Generate query variations
        query_variations = self.generate_query_variations(query)

        logger.info(f"Searching with {len(query_variations)} query variations")

        # Store results by chunk_id to deduplicate
        results_by_chunk: dict = {}

        # Search with each variation
        for idx, q in enumerate(query_variations):
            logger.debug(f"Searching with variation {idx + 1}: {q}")

            try:
                # Search with this query variation
                # Request more results per query to ensure good coverage
                variation_results = search_function(q, top_k * 2)

                # Process results
                for content, score, metadata in variation_results:
                    chunk_id = metadata.get('chunk_id')

                    if chunk_id is None:
                        # If no chunk_id, use content hash as key
                        chunk_id = hash(content)

                    if chunk_id in results_by_chunk:
                        # Chunk already seen, aggregate scores
                        existing_score = results_by_chunk[chunk_id][1]

                        if self.aggregation_strategy == 'max':
                            # Take maximum score
                            new_score = max(existing_score, score)
                        elif self.aggregation_strategy == 'average':
                            # Average the scores
                            new_score = (existing_score + score) / 2
                        elif self.aggregation_strategy == 'weighted':
                            # Weight by query position (original query has more weight)
                            weight = 1.0 / (idx + 1)
                            new_score = existing_score + (score * weight)
                        else:
                            new_score = max(existing_score, score)

                        results_by_chunk[chunk_id] = (content, new_score, metadata)

                    else:
                        # New chunk, add it
                        results_by_chunk[chunk_id] = (content, score, metadata)

            except Exception as e:
                logger.warning(f"Search failed for variation '{q}': {str(e)}")
                continue

        # Convert to list and sort by score
        all_results = list(results_by_chunk.values())
        all_results.sort(key=lambda x: x[1], reverse=True)

        # Return top K results
        final_results = all_results[:top_k]

        logger.info(
            f"MultiQuery retrieval: {len(query_variations)} queries, "
            f"{len(results_by_chunk)} unique chunks, "
            f"returning top {len(final_results)}"
        )

        return final_results

    def set_num_variations(self, num: int):
        """
        Update the number of query variations.

        Args:
            num: New number of variations
        """
        if num < 1 or num > 10:
            logger.warning(f"Invalid num_variations: {num}, keeping current: {self.num_variations}")
            return

        self.num_variations = num
        logger.info(f"Updated num_variations to {num}")

    def set_aggregation_strategy(self, strategy: str):
        """
        Update the score aggregation strategy.

        Args:
            strategy: 'max', 'average', or 'weighted'
        """
        valid_strategies = {'max', 'average', 'weighted'}

        if strategy not in valid_strategies:
            logger.warning(
                f"Invalid aggregation strategy: {strategy}, "
                f"must be one of {valid_strategies}"
            )
            return

        self.aggregation_strategy = strategy
        logger.info(f"Updated aggregation strategy to {strategy}")


def create_multi_query_retriever(llm_model: Any) -> MultiQueryRetriever:
    """
    Factory function to create a MultiQueryRetriever with default settings.

    Args:
        llm_model: Gemini GenerativeModel instance

    Returns:
        Configured MultiQueryRetriever instance
    """
    config = get_config()

    retriever = MultiQueryRetriever(
        llm_model=llm_model,
        num_variations=config.num_query_variations,
        aggregation_strategy='max'  # Use max score by default
    )

    return retriever
