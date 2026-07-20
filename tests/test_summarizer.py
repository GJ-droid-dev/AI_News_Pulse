import pytest
from unittest.mock import patch, MagicMock
import os
from src.rag.summarizer import DigestSummarizer

@patch.dict(os.environ, {"GROQ_API_KEY": "fake_test_key"})
@patch("src.rag.summarizer.Groq")
def test_summarizer_primary_success(MockGroq):
    # Setup mock successful response from the primary 70B model
    mock_client = MockGroq.return_value
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "# AI News Pulse\nPrimary Digest generated."
    mock_client.chat.completions.create.return_value = mock_response
    
    summarizer = DigestSummarizer()
    digest = summarizer.generate_digest({"llm_models": "Test Context"}, "2026-07-20")
    
    assert digest == "# AI News Pulse\nPrimary Digest generated."
    mock_client.chat.completions.create.assert_called_once()
    
    # Verify the primary model was called
    called_args = mock_client.chat.completions.create.call_args[1]
    assert called_args["model"] == "llama-3.3-70b-versatile"

@patch.dict(os.environ, {"GROQ_API_KEY": "fake_test_key"})
@patch("src.rag.summarizer.Groq")
def test_summarizer_fallback(MockGroq):
    mock_client = MockGroq.return_value
    
    # Setup mock response for the fallback
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Fallback Digest generated."
    
    # First call throws exception (e.g. rate limit), second call succeeds
    mock_client.chat.completions.create.side_effect = [
        Exception("Groq API Rate Limit Exceeded 429"),
        mock_response
    ]
    
    summarizer = DigestSummarizer()
    digest = summarizer.generate_digest({"llm_models": "Test Context"}, "2026-07-20")
    
    assert digest == "Fallback Digest generated."
    assert mock_client.chat.completions.create.call_count == 2
    
    # Verify the fallback model was called on the second attempt
    second_call_args = mock_client.chat.completions.create.call_args_list[1][1]
    assert second_call_args["model"] == "llama-3.1-8b-instant"
