import pytest
from src.scrapers.html_scraper import HTMLScraper
from src.scrapers.rss_scraper import RSSScraper

def test_html_scraper_initialization():
    config = {
        "name": "Test HTML",
        "url": "https://example.com/feed",
        "type": "html",
        "category": "llm_models",
        "selectors": {"article_container": "div.article"}
    }
    scraper = HTMLScraper(config)
    assert scraper.name == "Test HTML"
    assert scraper.url == "https://example.com/feed"
    assert scraper.selectors["article_container"] == "div.article"

def test_rss_scraper_initialization():
    config = {
        "name": "Test RSS",
        "url": "https://example.com/rss",
        "type": "rss",
        "category": "research_papers"
    }
    scraper = RSSScraper(config)
    assert scraper.name == "Test RSS"
    assert scraper.url == "https://example.com/rss"
    assert scraper.category == "research_papers"
