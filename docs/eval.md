# AI News Pulse — Phase-Wise Evaluation Plan

> This document defines the evaluation criteria, testing strategies, and success metrics for each of the 6 implementation phases of the AI News Pulse system. It ensures that every component is rigorously validated before moving to the next phase.

---

## Phase 1: Project Setup & Infrastructure

**Objective:** Validate that all foundational infrastructure, dependencies, and database schemas are correctly provisioned and accessible.

### Evaluation Criteria
1. **Environment Initialization:**
   - Run a clean `pip install -r requirements.txt`. Ensure no dependency conflicts (especially around `FlagEmbedding`, `fastapi`, and `psycopg2`).
2. **Configuration Loading:**
   - Execute a unit test that parses `settings.yml`, `sources.yml`, and `subscribers.yml`. Verify that all keys map correctly to expected data types.
3. **Database Schema Verification:**
   - Connect to the PostgreSQL database and run `\dt`. Ensure `articles` and `digests` tables exist.
   - Insert a mock row into both tables and verify constraints (e.g., `url` uniqueness in `articles`, `date` uniqueness in `digests`).
4. **Vector Store Connectivity:**
   - Run a health check script against the Pinecone `ai-news-articles` index.
   - Verify index configuration: Dimensions must exactly equal `384` and the metric must be `cosine`.

---

## Phase 2: Ingestion Pipeline

**Objective:** Ensure the system can reliably scrape, clean, deduplicate, and store articles from the 12 configured sources.

### Evaluation Criteria
1. **Scraper Reliability & Rate Limiting:**
   - **Eval Method:** Trigger all scrapers simultaneously.
   - **Success:** No HTTP 429 (Too Many Requests) received. `robots_checker.py` correctly blocks scraping of disallowed paths.
2. **Cleaning & Normalization Quality:**
   - **Eval Method:** Pass 5 raw HTML files (with ads, navbars, and unicode issues) through `cleaner.py`.
   - **Success:** Output contains >95% main article text, 0% HTML tags, and passes `langdetect` for English.
3. **Deduplication Accuracy:**
   - **Eval Method:** Feed the deduplicator 3 articles with the same URL, 2 articles with slightly modified titles, and 2 completely distinct articles.
   - **Success:** Exact URL matches are dropped. Fuzzy title matches (>85% similarity via `rapidfuzz`) are flagged. Distinct articles pass through.
4. **Database Persistence:**
   - **Eval Method:** Check PostgreSQL `articles` table post-ingestion.
   - **Success:** `scraped_at` timestamp is populated. `body_hash` is correctly calculated.

---

## Phase 3: Embedding & Vector Store

**Objective:** Validate chunking logic, local embedding generation via BGE, and successful indexing in Pinecone.

### Evaluation Criteria
1. **Chunking Fidelity:**
   - **Eval Method:** Pass a 2000-word article to `RecursiveCharacterTextSplitter`.
   - **Success:** Chunks do not exceed 512 tokens. Boundary overlaps are exactly 50 tokens. Sentences are not broken mid-word.
2. **Embedding Generation (BGE):**
   - **Eval Method:** Pass a batch of 10 chunks to `embedder.py` (`BAAI/bge-small-en-v1.5`).
   - **Success:** The output is a list of 10 vectors. Every vector has a length of exactly `384`. Memory usage remains stable (no OOM).
3. **Vector Upsert & Retrieval:**
   - **Eval Method:** Upsert 50 mocked vectors to Pinecone under a test namespace.
   - **Success:** Querying the namespace immediately returns the vectors with all associated metadata (`source_name`, `published_date`, `url`).
4. **Idempotency Check:**
   - **Eval Method:** Attempt to upsert the exact same chunks twice.
   - **Success:** Pinecone does not duplicate the vectors (checked via vector IDs).

---

## Phase 4: RAG Digest Generation

**Objective:** Evaluate the quality of the LLM-generated digest, adherence to guardrails, and handling of context limits.

### Evaluation Criteria
1. **Context Relevance (Retrieval Eval):**
   - **Eval Method:** Query the vector store using the 6 category seed queries.
   - **Success:** Top-K results for "Startups & Funding" must explicitly mention funding, VCs, or acquisitions. Cosine similarity scores must be >0.70.
2. **Summarization Quality & Guardrails:**
   - **Eval Method:** Generate a digest using historical chunk data. Pass the output through a secondary LLM "judge" prompt to check constraints.
   - **Success:** 
     - 0% presence of financial advice or subjective predictions.
     - 100% of bullet points contain a markdown citation link to the source.
     - Tone is neutral.
3. **Groq API Resilience:**
   - **Eval Method:** Simulate a timeout or 429 on `llama-3.3-70b-versatile`.
   - **Success:** The system automatically falls back to `llama-3.1-8b-instant` and successfully generates the digest within 30 seconds.
4. **JSON Formatting:**
   - **Eval Method:** Validate the LLM output against the predefined Pydantic/JSON schema.
   - **Success:** No schema validation errors; the frontend can parse it directly.

---

## Phase 5: API & Frontend

**Objective:** Validate that the REST API serves the generated digests correctly and the frontend renders seamlessly.

### Evaluation Criteria
1. **API Endpoint Functionality:**
   - **Eval Method:** Run integration tests via `pytest` and `httpx` against all 4 endpoints (`/today`, `/{date}`, `/archive`, `/health`).
   - **Success:** `/today` returns 200 OK with the latest JSON. Invalid dates return 404.
2. **Frontend Rendering & Responsiveness:**
   - **Eval Method:** Open `index.html` on a desktop browser (1920x1080) and a mobile emulator (375x667).
   - **Success:** Category sections collapse/expand cleanly. The "Highlight of the Day" hero card renders prominently. No horizontal scrolling on mobile.
3. **Theme & State Persistence:**
   - **Eval Method:** Toggle Dark Mode. Refresh the page.
   - **Success:** The UI remembers the dark mode preference via `localStorage`.

---

## Phase 6: Scheduler, CI/CD & Polish

**Objective:** Prove that the entire system can run autonomously on a schedule, recover from errors, and clean up after itself.

### Evaluation Criteria
1. **End-to-End Pipeline Dry Run:**
   - **Eval Method:** Trigger the GitHub Actions workflow manually (`workflow_dispatch`).
   - **Success:** The pipeline executes Scrape → Embed → Generate → Publish in under 15 minutes. The frontend updates immediately.
2. **Automated Notification Delivery:**
   - **Eval Method:** Check the configured SendGrid/SES email inbox.
   - **Success:** The digest email arrives well-formatted (Markdown/HTML) with correct links.
3. **TTL & Data Retention Cleanup:**
   - **Eval Method:** Manually insert an article and a Pinecone vector with a `published_date` of 40 days ago. Run the cleanup script.
   - **Success:** The outdated article and vector are completely deleted. Today's articles remain untouched.
4. **Cron Trigger Verification:**
   - **Eval Method:** Monitor the Actions tab at 9:00 AM IST.
   - **Success:** The pipeline boots automatically exactly on schedule.

---

> **Document Version:** 1.0
> **Created:** 19 Jul 2026
> **Aligned With:** [implementation_plan.md](file:///c:/Users/Admin/Documents/Article%20reader%20project/docs/implementation_plan.md)
