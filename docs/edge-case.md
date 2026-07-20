# AI News Pulse — Edge Cases and Corner Scenarios

> This document outlines potential edge cases, failure modes, and corner scenarios for the AI News Pulse system, derived from the system architecture and implementation plan. It details how the system should handle these anomalies gracefully to ensure uninterrupted zero-touch operation.

---

## 1. Data Ingestion & Scraping Scenarios

### 1.1 Source Layout Changes
- **Scenario:** A source website updates its DOM structure, breaking the BeautifulSoup CSS selectors defined in `config/sources.yml`.
- **Handling:** The scraper must wrap extraction logic in `try-except` blocks. If extraction fails, it should log an error for that specific source, return `0` articles, and proceed to the next source. The digest will simply be generated without that source's content.

### 1.2 Scraper Blocking (403 Forbidden / Captcha)
- **Scenario:** A source website starts blocking the scraper due to bot detection (e.g., Cloudflare).
- **Handling:** HTTP 403s should be caught gracefully. Log a warning and skip the source. Long-term mitigation involves rotating user agents or adapting the scraping frequency.

### 1.3 Empty or Extremely Short Content
- **Scenario:** The scraper successfully parses a page, but the main body content is hidden behind a paywall or JavaScript, resulting in <100 characters of text.
- **Handling:** The `cleaner.py` module must enforce a minimum length filter (e.g., `min_chars=100`). Articles failing this check are discarded immediately.

### 1.4 Date Parsing Ambiguities
- **Scenario:** An article contains a relative date (e.g., "3 hours ago") or is published late at night in a different time zone.
- **Handling:** `dateutil.parser` is used for robust parsing. All dates must be normalized to a standard timezone (e.g., UTC) upon ingestion. If no date is found, default to the `scraped_at` timestamp.

### 1.5 Foreign Language Articles
- **Scenario:** An article is published in French or Spanish on a monitored RSS feed.
- **Handling:** `cleaner.py` uses `langdetect` to verify the language. Non-English articles are flagged and excluded from the embedding pipeline.

---

## 2. Processing & Deduplication Scenarios

### 2.1 The "Echo Chamber" (Same Story, Many Sources)
- **Scenario:** OpenAI announces a new model, and 8 of the 12 monitored sources write an article about it.
- **Handling:** The `deduplicator.py` script uses URL canonicalization and fuzzy title matching (via `rapidfuzz` with >85% similarity). It retains the earliest published version and flags the rest as `duplicate`. Only the canonical version is embedded.

### 2.2 Title Updates Post-Publication
- **Scenario:** A source publishes an article and changes the headline 2 hours later.
- **Handling:** If the canonical URL remains the same, the deduplication engine will identify it via URL match and skip re-embedding.

### 2.3 Extremely Long Articles
- **Scenario:** A 15,000-word deep-dive article is ingested, potentially skewing retrieval or exhausting Pinecone storage.
- **Handling:** The `RecursiveCharacterTextSplitter` handles the chunking. However, a `max_chunks_per_article` limit (e.g., 20 chunks) should be enforced to prevent single articles from dominating the vector space.

---

## 3. Embedding & Vector Store Scenarios

### 3.1 Local OOM (Out of Memory) During Embedding
- **Scenario:** Generating embeddings using BGE (`BAAI/bge-small-en-v1.5`) crashes the GitHub Actions runner due to memory limits.
- **Handling:** Ensure `FlagEmbedding` processes chunks in small, fixed-size batches (e.g., `batch_size=16` or `32`). Do not pass all daily chunks to the embedder simultaneously.

### 3.2 Pinecone API Timeout or Outage
- **Scenario:** The Pinecone serverless endpoint times out during the batch upsert.
- **Handling:** Implement an exponential backoff retry mechanism (e.g., 3 retries, base delay 2s). If all retries fail, fail the GitHub Actions workflow so it can be manually re-run later (idempotency is crucial here).

### 3.3 Zombie Vectors (Storage Limits)
- **Scenario:** Over time, the free tier Pinecone index (100K limit) fills up with outdated news.
- **Handling:** A TTL cleanup routine in `vector_store.py` runs before each upsert, deleting all vectors where `published_date < (today - 30 days)`.

---

## 4. LLM & Digest Generation Scenarios

### 4.1 Zero Relevant Articles for a Category
- **Scenario:** It's a slow news day. No articles match the "Policy & Regulation" seed query above the similarity threshold (0.70).
- **Handling:** The semantic retriever returns an empty list for that category. The system prompt instructs the LLM to simply omit categories with no context. The final JSON formatter must gracefully handle missing categories.

### 4.2 Groq Rate Limits or API Outage
- **Scenario:** The primary Groq model (`llama-3.3-70b-versatile`) returns a 429 Rate Limit or 503 Server Error.
- **Handling:** Catch the exception, apply a brief sleep, and fallback to the `llama-3.1-8b-instant` model. If the fallback also fails after 3 retries, the pipeline writes a "Service Degraded" placeholder digest to the database.

### 4.3 LLM Hallucinated Citations
- **Scenario:** The LLM hallucinates a source name or provides a broken URL for a bullet point.
- **Handling:** The system prompt rigidly restricts output formats. Additionally, the `formatter.py` script can post-process the Markdown to verify that all emitted URLs match the URLs provided in the injected context block. If an unverified URL is found, strip the bullet point.

### 4.4 Maximum Token Limit Exceeded
- **Scenario:** The context provided to the LLM is too large, causing the generated response to cut off mid-sentence due to `max_tokens`.
- **Handling:** Limit the `Top-K` retrieval strictly to 5-10 chunks per category. Enforce a hard truncation on the context string size before sending it to the Groq API.

---

## 5. Delivery & Frontend Scenarios

### 5.1 No New Articles Scraped (Empty Digest)
- **Scenario:** All scrapers fail, or it's a holiday with absolutely no AI news published.
- **Handling:** The pipeline detects 0 new embedded chunks. It skips LLM generation and directly publishes a valid JSON digest indicating: "No significant AI news updates today."

### 5.2 PostgreSQL Connection Failure
- **Scenario:** The FastAPI backend cannot reach the Neon/Supabase PostgreSQL database.
- **Handling:** The `/health` endpoint returns 503. The frontend displays a friendly "Systems currently undergoing maintenance" UI instead of a raw traceback.

### 5.3 Missing "Highlight of the Day"
- **Scenario:** The LLM fails to output the designated Highlight section due to prompt disobedience.
- **Handling:** `formatter.py` detects the missing highlight. It falls back to selecting the first bullet point of the first populated category as the highlight programmatically.

---

## 6. System & Infrastructure Scenarios

### 6.1 GitHub Actions Runner Timeout
- **Scenario:** The ingestion pipeline gets stuck waiting on a hanging HTTP connection, causing the 15-minute GitHub Action timeout to kill the job.
- **Handling:** Enforce strict timeouts on the `requests` library (e.g., `timeout=10`). If the action still times out, the `continue-on-error` configuration handles subsequent re-runs manually.

### 6.2 Partial Pipeline Failure
- **Scenario:** Scrape and embed succeed, but generation fails.
- **Handling:** Because the system is idempotent and uses the current date as the key, running the pipeline again will quickly skip the scraping/embedding steps (deduplication catches them) and retry the generation step.
