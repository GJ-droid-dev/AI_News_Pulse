import logging
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

class ArticleChunker:
    def __init__(self, chunk_size: int = 1500, chunk_overlap: int = 150):
        """
        Initializes the chunker. Uses RecursiveCharacterTextSplitter to split
        long articles into smaller, semantically coherent chunks for embedding.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Recursive splitter tries to split by double newline, then newline, then space
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )

    def chunk_article(self, article: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Takes an article dictionary and chunks its 'body_text'.
        Returns a list of dictionaries, where each dict has the 'text' of the chunk
        and a 'metadata' dictionary containing info about the parent article.
        """
        body_text = article.get("body_text", "")
        if not body_text:
            return []
            
        chunks_text = self.splitter.split_text(body_text)
        
        # Prepare metadata to attach to each chunk
        metadata_base = {
            "article_id": str(article.get("id", "")),
            "url": article.get("url", ""),
            "title": article.get("title", ""),
            "source_name": article.get("source_name", ""),
            "category": article.get("category", ""),
            "published_date": str(article.get("published_date", "")),
        }
        
        chunks = []
        for i, text in enumerate(chunks_text):
            chunk_dict = {
                "text": text,
                "metadata": metadata_base.copy()
            }
            chunk_dict["metadata"]["chunk_index"] = i
            chunks.append(chunk_dict)
            
        return chunks
