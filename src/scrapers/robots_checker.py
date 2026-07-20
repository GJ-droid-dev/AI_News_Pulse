import urllib.robotparser
from urllib.parse import urlparse
import requests
import logging

logger = logging.getLogger(__name__)

class RobotsChecker:
    """
    Utility to cache and check robots.txt compliance for various domains.
    Uses an explicit HTTP timeout to prevent hanging on slow servers.
    """
    def __init__(self, user_agent: str = "AINewsPulseBot/1.0"):
        self.user_agent = user_agent
        self.parsers = {}

    def is_allowed(self, url: str) -> bool:
        """
        Returns True if the given URL is allowed to be scraped for the configured User-Agent.
        Defaults to True if robots.txt cannot be fetched or parsed.
        """
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        robots_url = f"{base_url}/robots.txt"

        # Fetch and cache robots.txt if not already loaded for this domain
        if base_url not in self.parsers:
            rp = urllib.robotparser.RobotFileParser()
            try:
                logger.debug(f"Fetching {robots_url}")
                # 5-second timeout to prevent the ingestion pipeline from hanging
                response = requests.get(robots_url, timeout=5, headers={"User-Agent": self.user_agent})
                if response.status_code == 200:
                    rp.parse(response.text.splitlines())
                self.parsers[base_url] = rp
            except Exception as e:
                logger.warning(f"Failed to fetch {robots_url}: {e}. Defaulting to allowed.")
                self.parsers[base_url] = None

        rp = self.parsers.get(base_url)
        if rp is None:
            return True

        return rp.can_fetch(self.user_agent, url)

# Singleton instance to be used across the scraping pipeline
default_checker = RobotsChecker()

def check_url_allowed(url: str) -> bool:
    """Convenience wrapper for the singleton instance."""
    return default_checker.is_allowed(url)
