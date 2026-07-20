import os
import logging
from typing import Dict
# pyrefly: ignore [missing-import]
from groq import Groq
from src.rag.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

class DigestSummarizer:
    def __init__(self):
        """Initializes the Groq client for LLM generation."""
        self.api_key = os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set. Cannot initialize Groq client.")
            
        self.client = Groq(api_key=self.api_key)
        self.primary_model = "llama-3.3-70b-versatile"
        self.fallback_model = "llama-3.1-8b-instant"
        
    def generate_digest(self, category_contexts: Dict[str, str], target_date: str) -> str:
        """
        Assembles the context blocks for all 6 categories, injects them into the User Prompt,
        and calls the Groq API to synthesize the final markdown digest.
        
        Implements an automatic fallback to an 8B model if the 70B model fails or rate-limits.
        """
        logger.info(f"Generating RAG digest for {target_date}...")
        
        # 1. Assemble the massive context block from all categories
        context_chunks_str = ""
        for category, context in category_contexts.items():
            context_chunks_str += f"\n\n### Category: {category} ###\n{context}"
            
        # 2. Format the user prompt with the injected context
        user_prompt = USER_PROMPT_TEMPLATE.format(
            date=target_date,
            context_chunks=context_chunks_str
        )
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        # 3. Call the primary 70B model with a fallback mechanism to 8B
        try:
            logger.info(f"Calling primary Groq model: {self.primary_model}")
            response = self.client.chat.completions.create(
                model=self.primary_model,
                messages=messages,
                temperature=0.1,  # Low temperature to strictly enforce factual RAG extraction
                max_tokens=2500,  # Ensure enough space for a comprehensive daily digest
            )
            logger.info("✅ Successfully generated digest using primary model.")
            return response.choices[0].message.content
            
        except Exception as e:
            logger.warning(f"⚠️ Primary model ({self.primary_model}) failed: {e}. Falling back to {self.fallback_model}...")
            try:
                response = self.client.chat.completions.create(
                    model=self.fallback_model,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=2500,
                )
                logger.info("✅ Successfully generated digest using fallback model.")
                return response.choices[0].message.content
            except Exception as fallback_err:
                logger.error(f"❌ Fallback model also failed: {fallback_err}")
                raise
