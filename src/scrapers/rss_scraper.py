from typing import List, Dict, Any
import feedparser
import requests
from bs4 import BeautifulSoup
import logging

from src.scrapers.base_scraper import BaseScraper
from src.scrapers.robots_checker import check_url_allowed

logger = logging.getLogger(__name__)

class RSSScraper(BaseScraper):
    def __init__(self, source_config: Dict[str, Any]):
        super().__init__(source_config)
        self.headers = {"User-Agent": "AINewsPulseBot/1.0"}

    def is_allowed(self) -> bool:
        return check_url_allowed(self.url)

    def _fetch_article_body(self, url: str) -> str:
        """Fallback to fetch full text from the HTML page if the RSS only provides a short snippet."""
        if not check_url_allowed(url):
            return ""
            
        self._enforce_rate_limit()
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            paragraphs = soup.find_all("p")
            text_blocks = [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 50]
            return "\n\n".join(text_blocks)
        except Exception as e:
            logger.debug(f"[{self.name}] Failed to fetch full article body from {url}: {e}")
            return ""

    def scrape(self) -> List[Dict[str, Any]]:
        articles = []
        if not self.is_allowed():
            logger.warning(f"[{self.name}] robots.txt forbids scraping RSS feed: {self.url}")
            return articles

        logger.info(f"[{self.name}] Scraping RSS feed: {self.url}")
        
        try:
            # We fetch via requests to strictly control timeouts and User-Agent headers
            response = requests.get(self.url, headers=self.headers, timeout=10)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
        except Exception as e:
            logger.error(f"[{self.name}] Failed to fetch RSS feed: {e}")
            return articles

        if feed.bozo:
            logger.warning(f"[{self.name}] Feedparser reported bozo exception (malformed XML), but will attempt parsing anyway.")

        entries = feed.entries
        logger.debug(f"[{self.name}] Found {len(entries)} entries in RSS feed.")

        for entry in entries:
            try:
                title = entry.get("title", "")
                link = entry.get("link", "")
                
                # Feeds vary in how they represent publish dates
                published_date = entry.get("published", entry.get("updated", None))

                if not title or not link:
                    continue

                # Try to get content from RSS directly, stripping any embedded HTML tags
                body_text = ""
                if "content" in entry and len(entry.content) > 0:
                    body_text = BeautifulSoup(entry.content[0].value, "html.parser").get_text(strip=True)
                elif "summary" in entry:
                    body_text = BeautifulSoup(entry.summary, "html.parser").get_text(strip=True)

                # If the body is too short (e.g. just a teaser/snippet), fetch the real article page
                if len(body_text) < 500:
                    full_text = self._fetch_article_body(link)
                    if full_text:
                        body_text = full_text

                if not body_text:
                    continue

                articles.append({
                    "title": title,
                    "url": link,
                    "source_name": self.name,
                    "category": self.category,
                    "body_text": body_text,
                    "published_date": published_date,
                    "language": "en"
                })

            except Exception as e:
                logger.error(f"[{self.name}] Error parsing an RSS entry: {e}")
                continue

        logger.info(f"[{self.name}] Successfully scraped {len(articles)} articles.")
        return articles
