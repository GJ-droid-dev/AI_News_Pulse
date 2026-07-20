import hashlib
import logging
from typing import Dict, Any, List
from rapidfuzz import fuzz
from src.storage.article_store import ArticleStore

logger = logging.getLogger(__name__)

class Deduplicator:
    """
    Handles deduplication of articles using a 3-tier approach:
    1. Exact URL match
    2. Content Hash (SHA-256) exact match
    3. Fuzzy Title match (RapidFuzz >= 85%)
    """
    def __init__(self, article_store: ArticleStore, threshold: float = 85.0):
        self.store = article_store
        self.threshold = threshold
        self.recent_articles = []
        self._load_recent_articles()

    def _load_recent_articles(self):
        """Loads articles from the last 7 days into memory for fast deduplication comparison."""
        query = """
            SELECT url, title, body_hash 
            FROM articles 
            WHERE scraped_at >= NOW() - INTERVAL '7 days'
        """
        try:
            with self.store.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
                    self.recent_articles = cur.fetchall()
            logger.info(f"Loaded {len(self.recent_articles)} recent articles into memory for deduplication.")
        except Exception as e:
            logger.error(f"Failed to load recent articles from DB for deduplication: {e}")
            self.recent_articles = []

    def compute_hash(self, text: str) -> str:
        """Computes a SHA-256 hash of the text."""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def is_duplicate(self, article: Dict[str, Any]) -> bool:
        """
        Checks if the article is a duplicate based on the recent cache.
        Also calculates and sets the 'body_hash' key on the article dictionary.
        """
        url = article.get("url", "")
        title = article.get("title", "")
        body_text = article.get("body_text", "")
        
        # Calculate hash and attach it to the dict so the orchestrator can easily insert it to the DB later
        body_hash = self.compute_hash(body_text)
        article["body_hash"] = body_hash

        for row in self.recent_articles:
            # 1. Exact URL Match
            if url == row["url"]:
                logger.debug(f"Duplicate found (URL Match): {url}")
                return True
                
            # 2. Exact Hash Match
            if body_hash == row["body_hash"]:
                logger.debug(f"Duplicate found (Hash Match): '{title}'")
                return True

            # 3. Fuzzy Title Match
            similarity = fuzz.ratio(title.lower(), row["title"].lower())
            if similarity >= self.threshold:
                logger.debug(f"Duplicate found (Fuzzy Title Match - {similarity:.1f}%): '{title}' matches '{row['title']}'")
                return True

        # If it's not a duplicate, we should technically add it to our in-memory cache 
        # so subsequent articles in the same batch don't duplicate each other.
        self.recent_articles.append({
            "url": url,
            "title": title,
            "body_hash": body_hash
        })
        return False
