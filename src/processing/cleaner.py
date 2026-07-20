import re
import unicodedata
import logging
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from langdetect import detect, DetectorFactory
import langdetect

# Seed for consistent language detection
DetectorFactory.seed = 0

logger = logging.getLogger(__name__)

class ArticleCleaner:
    def __init__(self, min_length: int = 300):
        """
        Initializes the cleaner with a minimum character length for valid articles.
        Default is 300 characters (~50 words).
        """
        self.min_length = min_length

    def clean_text(self, raw_text: str) -> str:
        """
        Strips residual HTML, normalizes Unicode (removes smart quotes/NBSPs),
        and collapses excessive whitespace/newlines.
        """
        if not raw_text:
            return ""

        # 1. Strip residual HTML tags just in case
        soup = BeautifulSoup(raw_text, "html.parser")
        text = soup.get_text(separator=" ")

        # 2. Normalize Unicode
        text = unicodedata.normalize("NFKD", text)

        # 3. Collapse whitespace and newlines
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def process_article(self, article: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Cleans the article text and enforces quality filters (length and language).
        Returns the cleaned article dict, or None if it fails the filters.
        """
        cleaned_body = self.clean_text(article.get("body_text", ""))
        
        # Filter: Minimum Length
        if len(cleaned_body) < self.min_length:
            logger.debug(f"Article '{article.get('title')}' dropped: Body too short ({len(cleaned_body)} chars).")
            return None

        # Filter: Language Detection (Must be English to match our BGE model capabilities)
        try:
            lang = detect(cleaned_body)
            if lang != 'en':
                logger.debug(f"Article '{article.get('title')}' dropped: Non-English language detected ('{lang}').")
                return None
            article["language"] = lang
        except langdetect.lang_detect_exception.LangDetectException as e:
            logger.warning(f"Could not detect language for '{article.get('title')}': {e}. Dropping article.")
            return None

        # Clean title as well
        article["title"] = self.clean_text(article.get("title", ""))
        article["body_text"] = cleaned_body

        return article
