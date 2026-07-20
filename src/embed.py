import sys
import logging
import uuid
from pathlib import Path

# Add project root to sys path so we can run this script directly from anywhere
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.utils.logger import setup_logger
from src.utils.date_utils import get_current_utc_time, format_date_for_db
from src.storage.article_store import ArticleStore
from src.storage.vector_store import VectorStore
from src.processing.chunker import ArticleChunker
from src.processing.embedder import ArticleEmbedder

logger = setup_logger("embed_pipeline")

def main():
    logger.info("🚀 Starting AI News Pulse Embedding Pipeline...")
    
    # 1. Determine Target Date (Today)
    # We embed articles whose published_date matches today's date.
    target_date = format_date_for_db(get_current_utc_time())
    logger.info(f"Target embedding date: {target_date}")
    
    # 2. Initialize Components
    try:
        store = ArticleStore()
        v_store = VectorStore()
        chunker = ArticleChunker(chunk_size=1500, chunk_overlap=150)
        embedder = ArticleEmbedder(model_name="BAAI/bge-small-en-v1.5")
    except Exception as e:
        logger.error(f"Failed to initialize components: {e}")
        sys.exit(1)
        
    # 3. Fetch Articles from Database
    articles = store.get_articles_by_date(target_date)
    if not articles:
        logger.info(f"No articles found in the database for date {target_date}. Exiting.")
        sys.exit(0)
        
    logger.info(f"Found {len(articles)} articles to process.")

    total_chunks_upserted = 0
    # Isolate each day's embeddings into its own Pinecone namespace for easy TTL cleanup
    namespace = f"digest-{target_date}"
    
    # 4. Process, Embed, and Upsert
    for article in articles:
        try:
            title = article.get("title", "Unknown Title")
            logger.info(f"Processing article: '{title}'")
            
            # A. Chunking
            chunks = chunker.chunk_article(article)
            if not chunks:
                continue
                
            logger.debug(f"Created {len(chunks)} chunks.")
            
            # B. Embedding
            embedded_chunks = embedder.embed_chunks(chunks)
            
            # C. Formatting for Pinecone
            pinecone_vectors = []
            import hashlib
            for chunk in embedded_chunks:
                # Add the actual text payload into the metadata so the RAG pipeline can read it upon retrieval
                metadata = chunk["metadata"]
                metadata["text"] = chunk["text"]
                
                # Deterministic ID for idempotency: article_id + chunk_index
                id_str = f"{metadata['article_id']}_{metadata['chunk_index']}"
                deterministic_id = hashlib.md5(id_str.encode()).hexdigest()
                
                pinecone_vectors.append({
                    "id": deterministic_id,
                    "values": chunk["values"],
                    "metadata": metadata
                })
                
            # D. Upserting Batch
            v_store.upsert_batch(pinecone_vectors, namespace=namespace)
            total_chunks_upserted += len(pinecone_vectors)
            
        except Exception as e:
            logger.error(f"Failed to process article '{article.get('title')}': {e}")
            continue

    logger.info(f"✅ Embedding Pipeline Complete! Upserted {total_chunks_upserted} total chunks to Pinecone namespace '{namespace}'.")

if __name__ == "__main__":
    main()
