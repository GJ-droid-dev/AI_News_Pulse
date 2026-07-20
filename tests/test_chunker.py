import pytest
from src.processing.chunker import ArticleChunker

@pytest.fixture
def chunker():
    # Use a small chunk size for testing splits easily
    return ArticleChunker(chunk_size=100, chunk_overlap=20)

def test_chunk_article_empty(chunker):
    article = {"title": "Empty", "body_text": ""}
    chunks = chunker.chunk_article(article)
    assert chunks == []

def test_chunk_article_metadata(chunker):
    article = {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "title": "Test Title",
        "url": "https://example.com/test",
        "source_name": "Test Source",
        "category": "llm_models",
        "published_date": "2026-07-20",
        "body_text": "This is a short body text that fits in one chunk."
    }
    chunks = chunker.chunk_article(article)
    assert len(chunks) == 1
    
    metadata = chunks[0]["metadata"]
    assert metadata["article_id"] == "123e4567-e89b-12d3-a456-426614174000"
    assert metadata["title"] == "Test Title"
    assert metadata["url"] == "https://example.com/test"
    assert metadata["source_name"] == "Test Source"
    assert metadata["category"] == "llm_models"
    assert metadata["published_date"] == "2026-07-20"
    assert metadata["chunk_index"] == 0

def test_chunk_article_splitting(chunker):
    # A text long enough to be split into multiple chunks given chunk_size=100
    long_text = "A" * 90 + " " + "B" * 90
    article = {"title": "Long text", "body_text": long_text}
    
    chunks = chunker.chunk_article(article)
    assert len(chunks) > 1
    
    # Check that metadata index increments
    assert chunks[0]["metadata"]["chunk_index"] == 0
    assert chunks[1]["metadata"]["chunk_index"] == 1
    
    # Ensure text is properly stored
    assert "A" * 90 in chunks[0]["text"]
