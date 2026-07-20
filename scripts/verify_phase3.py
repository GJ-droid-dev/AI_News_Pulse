import sys
import logging
from pathlib import Path
import os

# Add project root to sys path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.utils.logger import setup_logger
from src.processing.embedder import ArticleEmbedder
from src.storage.vector_store import VectorStore

# Try loading dotenv if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = setup_logger("verify_phase3")

def main():
    logger.info("Starting Phase 3 Verification...")
    
    # 1. Verify Embedder
    logger.info("1. Verifying ArticleEmbedder (Local BGE Model)...")
    try:
        embedder = ArticleEmbedder()
        
        # Test document embedding
        sample_chunk = [{"text": "This is a test chunk to verify the local embedding model."}]
        embedded = embedder.embed_chunks(sample_chunk)
        vector = embedded[0]["values"]
        
        if len(vector) == 384:
            logger.info(f"✅ Embedder successfully generated 384-dimensional vector for document.")
        else:
            logger.error(f"❌ Embedder generated vector of length {len(vector)} (expected 384).")
            
        # Test query embedding
        query_vector = embedder.embed_query("Test search query")
        if len(query_vector) == 384:
            logger.info(f"✅ Embedder successfully generated 384-dimensional vector for query.")
        else:
            logger.error(f"❌ Embedder query vector has length {len(query_vector)} (expected 384).")
            
    except Exception as e:
        logger.error(f"❌ Embedder verification failed: {e}")

    # 2. Verify Vector Store
    logger.info("2. Verifying VectorStore (Pinecone Connection)...")
    try:
        v_store = VectorStore()
        stats = v_store.index.describe_index_stats()
        logger.info(f"✅ Successfully connected to Pinecone!")
        logger.info(f"Index stats: {stats}")
    except Exception as e:
        logger.error(f"❌ VectorStore verification failed: {e}")
        logger.info("Note: This failure is expected if PINECONE_API_KEY is not set in the environment or .env file.")

if __name__ == "__main__":
    main()
