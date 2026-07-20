from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging

from src.scrapers.base_scraper import BaseScraper
from src.scrapers.robots_checker import check_url_allowed

logger = logging.getLogger(__name__)

class HTMLScraper(BaseScraper):
    def __init__(self, source_config: Dict[str, Any]):
        super().__init__(source_config)
        self.headers = {"User-Agent": "AINewsPulseBot/1.0"}

    def is_allowed(self) -> bool:
        return check_url_allowed(self.url)

    def _fetch_page(self, url: str) -> str:
        self._enforce_rate_limit()
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"[{self.name}] Failed to fetch {url}: {e}")
            return ""

    def _extract_body_text(self, article_url: str) -> str:
        """Fetches the article page and extracts text from <p> tags."""
        if not check_url_allowed(article_url):
            logger.warning(f"[{self.name}] robots.txt forbids scraping article: {article_url}")
            return ""

        html = self._fetch_page(article_url)
        if not html:
            return ""

        soup = BeautifulSoup(html, "html.parser")
        
        # Simple heuristic: extract text from all <p> tags.
        paragraphs = soup.find_all("p")
        # Filter out very short paragraphs (often nav links or footers)
        text_blocks = [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 50]
        
        return "\n\n".join(text_blocks)

    def scrape(self) -> List[Dict[str, Any]]:
        articles = []
        if not self.is_allowed():
            logger.warning(f"[{self.name}] robots.txt forbids scraping main URL: {self.url}")
            return articles

        logger.info(f"[{self.name}] Scraping HTML feed: {self.url}")
        html = self._fetch_page(self.url)
        if not html:
            return articles

        soup = BeautifulSoup(html, "html.parser")
        
        container_sel = self.selectors.get("article_container")
        if not container_sel:
            logger.error(f"[{self.name}] No article_container selector provided.")
            return articles
            
        containers = soup.select(container_sel)
        logger.debug(f"[{self.name}] Found {len(containers)} article containers.")

        for container in containers:
            try:
                # Extract Title
                title_sel = self.selectors.get("title")
                title_elem = container.select_one(title_sel) if title_sel else container
                title = title_elem.get_text(strip=True) if title_elem else ""

                # Extract Link
                link_sel = self.selectors.get("link")
                link_elem = container.select_one(link_sel) if link_sel else container.find("a")
                
                # If the container itself is the link (e.g., Hugging Face a.blog-card)
                if not link_elem and container.name == "a":
                    link_elem = container
                    
                href = link_elem.get("href") if link_elem else ""
                article_url = urljoin(self.url, href) if href else ""

                # Extract Date (if possible)
                date_sel = self.selectors.get("date")
                date_elem = container.select_one(date_sel) if date_sel else None
                published_date = date_elem.get_text(strip=True) if date_elem else None

                if not title or not article_url:
                    continue

                # Fetch full body text
                body_text = self._extract_body_text(article_url)
                
                if not body_text:
                    continue

                articles.append({
                    "title": title,
                    "url": article_url,
                    "source_name": self.name,
                    "category": self.category,
                    "body_text": body_text,
                    "published_date": published_date,
                    "language": "en" # Language will be rigorously checked later by cleaner.py
                })

            except Exception as e:
                logger.error(f"[{self.name}] Error parsing an article container: {e}")
                continue

        logger.info(f"[{self.name}] Successfully scraped {len(articles)} articles.")
        return articles
