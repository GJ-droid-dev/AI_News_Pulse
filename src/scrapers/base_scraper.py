from abc import ABC, abstractmethod
from typing import List, Dict, Any
import time
import logging

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """
    Abstract base class for all AI News Pulse scrapers.
    Defines the standard interface for fetching and parsing articles from sources.
    """
    
    def __init__(self, source_config: Dict[str, Any]):
        self.name = source_config.get("name", "Unknown Source")
        self.url = source_config.get("url", "")
        self.category = source_config.get("category", "general")
        self.rate_limit_ms = source_config.get("rate_limit_ms", 1000)
        self.selectors = source_config.get("selectors", {})
        
    def _enforce_rate_limit(self):
        """Sleeps for the configured rate limit to respect the server's load."""
        sleep_time = self.rate_limit_ms / 1000.0
        logger.debug(f"[{self.name}] Rate limiting: sleeping for {sleep_time}s")
        time.sleep(sleep_time)

    def is_allowed(self) -> bool:
        """
        Checks robots.txt compliance before scraping.
        Implementation will hook into the robots_checker module.
        """
        # Defaulting to True for the base interface, to be properly wired in the orchestrator or subclass
        return True
        
    @abstractmethod
    def scrape(self) -> List[Dict[str, Any]]:
        """
        Executes the scraping logic.
        Must be implemented by subclasses (e.g., HTMLScraper, RSSScraper).
        
        Returns:
            List[Dict[str, Any]]: A list of raw article dictionaries containing at minimum:
            - title (str)
            - url (str)
            - source_name (str)
            - category (str)
            - body_text (str)
            - published_date (str or None)
        """
        pass
