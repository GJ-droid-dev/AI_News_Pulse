import os
import logging
from typing import List, Dict, Any
# pyrefly: ignore [missing-import]
from pinecone import Pinecone
from src.utils.config_loader import ConfigLoader

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self):
        self.api_key = os.environ.get("PINECONE_API_KEY")
        if not self.api_key:
            raise ValueError("PINECONE_API_KEY environment variable is not set")
            
        self.config = ConfigLoader.load_settings()
        self.index_name = self.config["vector_store"]["index_name"]
        
        self.pc = Pinecone(api_key=self.api_key)
        self.index = self.pc.Index(self.index_name)

    def upsert_batch(self, vectors: List[Dict[str, Any]], namespace: str):
        """
        Upserts a batch of vectors into Pinecone under the given namespace.
        Vector format: {"id": "chunk_uuid", "values": [0.1, ...], "metadata": {...}}
        """
        if not vectors:
            logger.warning("Attempted to upsert empty vector batch.")
            return

        try:
            # Upsert in batches of 100 to avoid Pinecone API limits
            batch_size = 100
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                self.index.upsert(vectors=batch, namespace=namespace)
            logger.info(f"Upserted {len(vectors)} vectors to namespace '{namespace}'.")
        except Exception as e:
            logger.error(f"Failed to upsert batch to Pinecone: {e}")
            raise

    def query(self, query_vector: List[float], category: str, namespace: str, top_k: int = None) -> List[Dict[str, Any]]:
        """
        Queries Pinecone for the most similar chunks matching a specific category.
        """
        if top_k is None:
            top_k = self.config["vector_store"].get("top_k", 10)
            
        try:
            response = self.index.query(
                vector=query_vector,
                namespace=namespace,
                top_k=top_k,
                include_metadata=True,
                filter={"category": {"$eq": category}}
            )
            return response.get("matches", [])
        except Exception as e:
            logger.error(f"Failed to query Pinecone for category '{category}': {e}")
            return []

    def delete_namespace(self, namespace: str):
        """
        Deletes an entire namespace. Critical for the 30-day TTL data retention cleanup.
        """
        try:
            self.index.delete(delete_all=True, namespace=namespace)
            logger.info(f"Deleted entire namespace '{namespace}' from Pinecone.")
        except Exception as e:
            logger.error(f"Failed to delete namespace '{namespace}': {e}")
            raise
