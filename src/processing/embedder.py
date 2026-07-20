import logging
from typing import List, Dict, Any
# pyrefly: ignore [missing-import]
from FlagEmbedding import FlagModel

logger = logging.getLogger(__name__)

class ArticleEmbedder:
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        """
        Initializes the local BGE embedding model.
        """
        logger.info(f"Loading embedding model: {model_name}...")
        try:
            # use_fp16=True significantly speeds up inference on supported hardware
            self.model = FlagModel(
                model_name, 
                query_instruction_for_retrieval="Represent this sentence for searching relevant passages: ",
                use_fp16=True
            )
            logger.info("Embedding model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load FlagModel '{model_name}': {e}")
            raise

    def embed_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Takes a list of chunk dictionaries and generates embeddings for them.
        Updates each dictionary with a 'values' key containing the 384-dim vector.
        """
        if not chunks:
            return []

        # Extract just the text strings for the model
        texts = [chunk["text"] for chunk in chunks]
        
        logger.debug(f"Generating embeddings for {len(texts)} chunks...")
        try:
            # encode() is used for documents/passages (no instruction prefix needed)
            embeddings = self.model.encode(texts)
            
            # Re-attach the resulting vectors to our chunk dictionaries
            for i, chunk in enumerate(chunks):
                # Pinecone expects Python float lists, so we cast the numpy arrays
                chunk["values"] = [float(v) for v in embeddings[i]]
                
            return chunks
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise

    def embed_query(self, query_text: str) -> List[float]:
        """
        Embeds a single query string for retrieval.
        Uses encode_queries to automatically prepend the required instruction.
        """
        try:
            query_embedding = self.model.encode_queries([query_text])[0]
            return [float(v) for v in query_embedding]
        except Exception as e:
            logger.error(f"Failed to embed query: {e}")
            raise
