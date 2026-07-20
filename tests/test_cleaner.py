import pytest
from src.processing.cleaner import ArticleCleaner

@pytest.fixture
def cleaner():
    return ArticleCleaner(min_length=50)

def test_html_stripping(cleaner):
    raw_text = "<p>This is a <b>test</b>.</p>"
    cleaned = cleaner.clean_text(raw_text)
    assert cleaned == "This is a test ."

def test_unicode_normalization(cleaner):
    raw_text = "This is a\xa0test with smart quotes: \u201cHello\u201d"
    cleaned = cleaner.clean_text(raw_text)
    assert "This is a test" in cleaned

def test_whitespace_collapse(cleaner):
    raw_text = "This   has    too\n\nmuch   whitespace."
    cleaned = cleaner.clean_text(raw_text)
    assert cleaned == "This has too much whitespace."

def test_process_article_drops_short(cleaner):
    article = {"title": "Test", "body_text": "Too short."}
    assert cleaner.process_article(article) is None

def test_process_article_drops_non_english(cleaner):
    # Length meets minimum, but language is Spanish
    article = {"title": "Hola", "body_text": "Este es un artículo de prueba que es lo suficientemente largo pero no está en inglés."}
    assert cleaner.process_article(article) is None
