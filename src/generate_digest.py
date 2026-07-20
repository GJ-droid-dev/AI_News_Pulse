import sys
import logging
from pathlib import Path

# Add project root to sys path so we can run this script directly from anywhere
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.utils.logger import setup_logger
from src.utils.date_utils import get_current_utc_time, format_date_for_db
from src.rag.retriever import DigestRetriever
from src.rag.summarizer import DigestSummarizer
from src.rag.formatter import DigestFormatter
from src.storage.digest_store import DigestStore

logger = setup_logger("generate_digest")

def main():
    logger.info("🚀 Starting AI News Pulse Digest Generation Pipeline...")
    
    # 1. Determine target date (Defaults to today)
    target_date = format_date_for_db(get_current_utc_time())
    logger.info(f"Target digest date: {target_date}")
    
    # 2. Initialize Components
    try:
        retriever = DigestRetriever()
        summarizer = DigestSummarizer()
        formatter = DigestFormatter(output_dir="data/digests")
        store = DigestStore()
    except Exception as e:
        logger.error(f"Failed to initialize RAG components (Are PINECONE_API_KEY and GROQ_API_KEY set?): {e}")
        sys.exit(1)
        
    # 3. Retrieve Context from Pinecone
    try:
        logger.info("Step 1: Retrieving category contexts from Pinecone vector store...")
        category_contexts = retriever.retrieve_context(target_date)
    except Exception as e:
        logger.error(f"Failed during retrieval phase: {e}")
        sys.exit(1)

    # 4. Generate Digest via LLM (Groq)
    try:
        logger.info("Step 2: Synthesizing digest using Groq LLM (Llama 3)...")
        raw_markdown = summarizer.generate_digest(category_contexts, target_date)
    except Exception as e:
        logger.error(f"Failed during LLM generation phase: {e}")
        sys.exit(1)

    # 5. Format and Save Locally
    try:
        logger.info("Step 3: Formatting and saving markdown output...")
        structured_payload = formatter.format_and_save(raw_markdown, target_date)
    except Exception as e:
        logger.error(f"Failed during formatting phase: {e}")
        sys.exit(1)

    # 6. Save to PostgreSQL for the FastAPI backend
    try:
        logger.info("Step 4: Archiving structured digest into PostgreSQL...")
        store.insert_digest(structured_payload)
    except Exception as e:
        logger.error(f"Failed to store digest in database: {e}")
        sys.exit(1)

    logger.info(f"✅ Digest Generation Complete for {target_date}!")
    
if __name__ == "__main__":
    main()
