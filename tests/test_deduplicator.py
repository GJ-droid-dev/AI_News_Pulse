import pytest
from unittest.mock import MagicMock
from src.processing.deduplicator import Deduplicator
from src.storage.article_store import ArticleStore

@pytest.fixture
def mock_store():
    # Mock ArticleStore to prevent DB connection requirements during unit tests
    store = MagicMock(spec=ArticleStore)
    return store

@pytest.fixture
def deduplicator(mock_store):
    dedup = Deduplicator(article_store=mock_store, threshold=85.0)
    # Inject fake recent articles into the cache
    dedup.recent_articles = [
        {"url": "https://example.com/1", "title": "OpenAI releases new model", "body_hash": "abc123hash"},
        {"url": "https://example.com/2", "title": "Anthropic updates Claude", "body_hash": "def456hash"}
    ]
    return dedup

def test_exact_url_match(deduplicator):
    article = {"url": "https://example.com/1", "title": "Different Title", "body_text": "Different body"}
    assert deduplicator.is_duplicate(article) == True

def test_fuzzy_title_match(deduplicator):
    # Typos/slight changes in title, url is different, body is different
    article = {"url": "https://example.com/3", "title": "OpenAI releases a new model", "body_text": "Some text"}
    assert deduplicator.is_duplicate(article) == True

def test_content_hash_match(deduplicator):
    # Same hash implies exact same body text (syndicated content)
    deduplicator.compute_hash = MagicMock(return_value="def456hash")
    article = {"url": "https://example.com/4", "title": "Completely new title", "body_text": "Same body as anthropic"}
    assert deduplicator.is_duplicate(article) == True

def test_not_a_duplicate(deduplicator):
    article = {"url": "https://example.com/5", "title": "Google announces Gemini Pro", "body_text": "New body text here..."}
    assert deduplicator.is_duplicate(article) == False
    
    # Verify it got automatically added to the runtime cache to prevent intra-batch duplicates
    assert len(deduplicator.recent_articles) == 3
    assert deduplicator.recent_articles[-1]["url"] == "https://example.com/5"
