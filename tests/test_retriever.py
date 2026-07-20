import pytest
from unittest.mock import patch
from src.rag.retriever import DigestRetriever

@patch("src.rag.retriever.ArticleEmbedder")
@patch("src.rag.retriever.VectorStore")
def test_retriever_context(MockVectorStore, MockEmbedder):
    # Mock Embedder to return a dummy vector
    mock_embedder_instance = MockEmbedder.return_value
    mock_embedder_instance.embed_query.return_value = [0.1] * 384
    
    # Mock Pinecone query to return a dummy match
    mock_vstore_instance = MockVectorStore.return_value
    mock_vstore_instance.query.return_value = [
        {
            "score": 0.95,
            "metadata": {
                "source_name": "TestSource",
                "url": "http://test.com",
                "title": "Test Title",
                "text": "This is test content."
            }
        }
    ]
    
    retriever = DigestRetriever()
    contexts = retriever.retrieve_context(target_date="2026-07-20")
    
    # Ensure all 6 categories are populated
    assert "llm_models" in contexts
    assert "ai_agents" in contexts
    
    # Ensure the formatting matches what we expect for the LLM
    expected_content = "Source: [TestSource](http://test.com)"
    assert expected_content in contexts["llm_models"]
    assert "This is test content." in contexts["llm_models"]

@patch("src.rag.retriever.ArticleEmbedder")
@patch("src.rag.retriever.VectorStore")
def test_retriever_empty_matches(MockVectorStore, MockEmbedder):
    mock_embedder_instance = MockEmbedder.return_value
    mock_embedder_instance.embed_query.return_value = [0.1] * 384
    
    # Simulate Pinecone returning no matches for a category
    mock_vstore_instance = MockVectorStore.return_value
    mock_vstore_instance.query.return_value = []
    
    retriever = DigestRetriever()
    contexts = retriever.retrieve_context(target_date="2026-07-20")
    
    assert "No significant updates in this category today." in contexts["llm_models"]
