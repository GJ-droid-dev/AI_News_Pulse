import logging
from typing import Dict
from src.rag.prompts import SEED_QUERIES
from src.processing.embedder import ArticleEmbedder
from src.storage.vector_store import VectorStore
from src.utils.date_utils import get_current_utc_time, format_date_for_db

logger = logging.getLogger(__name__)

class DigestRetriever:
    def __init__(self):
        """Initializes the retriever with the local BGE embedder and Pinecone vector store connection."""
        logger.info("Initializing Digest Retriever...")
        self.embedder = ArticleEmbedder(model_name="BAAI/bge-small-en-v1.5")
        self.v_store = VectorStore()
        
    def retrieve_context(self, target_date: str = None) -> Dict[str, str]:
        """
        For each category defined in the seed queries, embeds the semantic search phrase,
        fetches the Top-K most relevant chunks from Pinecone, and formats them into
        a readable text block for the LLM context window.
        
        Returns a dictionary mapping category_name -> formatted_context_string.
        """
        if not target_date:
            target_date = format_date_for_db(get_current_utc_time())
            
        namespace = f"digest-{target_date}"
        logger.info(f"Retrieving context from Pinecone namespace: {namespace}")
        
        category_contexts = {}
        
        for category, query_text in SEED_QUERIES.items():
            logger.debug(f"Retrieving chunks for category: {category}")
            try:
                # 1. Embed the semantic seed query
                query_vector = self.embedder.embed_query(query_text)
                
                # 2. Fetch Top-K relevant chunks from Pinecone
                # Top 3 chunks per category gives the LLM rich context without overflowing the strict 12K TPM Groq limit
                matches = self.v_store.query(
                    query_vector=query_vector,
                    category=category,
                    namespace=namespace,
                    top_k=3
                )
                
                if not matches:
                    category_contexts[category] = "No significant updates in this category today."
                    continue
                
                # 3. Format the chunks into a structured Markdown string for the LLM Prompt
                formatted_chunks = []
                for match in matches:
                    metadata = match.get("metadata", {})
                    score = match.get("score", 0.0)
                    
                    # The format explicitly includes the URL and Source so the LLM can generate valid markdown citations
                    chunk_str = f"Source: [{metadata.get('source_name', 'Unknown')}]({metadata.get('url', '#')})\n"
                    chunk_str += f"Title: {metadata.get('title', 'Unknown')}\n"
                    chunk_str += f"Relevance Score: {score:.3f}\n"
                    chunk_str += f"Content: {metadata.get('text', '')}\n"
                    
                    formatted_chunks.append(chunk_str)
                
                # Join the retrieved chunks using a distinct separator
                category_contexts[category] = "\n---\n".join(formatted_chunks)
                
            except Exception as e:
                logger.error(f"Failed to retrieve context for category '{category}': {e}")
                category_contexts[category] = "Error retrieving context for this category."
                
        return category_contexts
