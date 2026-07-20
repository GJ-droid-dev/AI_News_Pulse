# AI News Pulse — Phase-Wise Implementation Plan

> Step-by-step build plan derived from [Architecture.md](file:///c:/Users/Admin/Documents/Article%20reader%20project/Architecture.md), broken into 6 phases with clear deliverables, files, and acceptance criteria per phase.

---

## Plan Overview

```mermaid
gantt
    title AI News Pulse — Implementation Timeline
    dateFormat  YYYY-MM-DD
    axisFormat  %d %b

    section Phase 1
    Project Setup & Infra           :p1, 2026-07-20, 2d

    section Phase 2
    Ingestion Pipeline              :p2, after p1, 4d

    section Phase 3
    Embedding & Vector Store        :p3, after p2, 3d

    section Phase 4
    RAG Digest Generation           :p4, after p3, 4d

    section Phase 5
    API & Frontend                  :p5, after p4, 4d

    section Phase 6
    Scheduler, CI/CD & Polish       :p6, after p5, 3d
```

| Phase | Name | Duration | Key Outcome |
|---|---|---|---|
| 1 | Project Setup & Infrastructure | 2 days | Repo scaffolding, dependencies, Pinecone index, PostgreSQL schema, config files |
| 2 | Ingestion Pipeline | 4 days | Scrape 12 sources, clean, deduplicate, store article metadata |
| 3 | Embedding & Vector Store | 3 days | Chunk articles, generate embeddings (BGE), index in Pinecone |
| 4 | RAG Digest Generation | 4 days | Category-seeded retrieval, Groq LLM summarization, digest formatting |
| 5 | API & Frontend | 4 days | FastAPI endpoints, read-only digest viewer with dark mode and archive |
| 6 | Scheduler, CI/CD & Polish | 3 days | GitHub Actions cron, email delivery, error handling, testing, documentation |

**Total estimated duration: ~20 days**

---

## Phase 1: Project Setup & Infrastructure

> **Goal:** Scaffold the project, install dependencies, provision external services, and create the database schema.

### 1.1 Tasks

| # | Task | Files Created / Modified |
|---|---|---|
| 1.1 | Initialize project directory structure as per Architecture.md | All directories under `ai-news-pulse/` |
| 1.2 | Create `requirements.txt` with all pinned dependencies | `requirements.txt` |
| 1.3 | Create Python virtual environment and install deps | — (CLI) |
| 1.4 | Set up `config/settings.yml` with global settings | `config/settings.yml` |
| 1.5 | Create `config/sources.yml` with all 12 source definitions | `config/sources.yml` |
| 1.6 | Create `config/subscribers.yml` (email config placeholder) | `config/subscribers.yml` |
| 1.7 | Write `src/utils/config_loader.py` (YAML parser) | `src/utils/config_loader.py` |
| 1.8 | Write `src/utils/logger.py` (structured logging) | `src/utils/logger.py` |
| 1.9 | Write `src/utils/date_utils.py` (date helpers) | `src/utils/date_utils.py` |
| 1.10 | Provision Pinecone serverless index (`ai-news-articles`, 384-dim matching BGE, cosine) | Pinecone Dashboard / CLI |
| 1.11 | Provision Neon (Serverless Postgres) database | Neon Dashboard |
| 1.12 | Create Neon (Serverless Postgres) Database for raw articles and final digests (Lightweight metadata) | `src/storage/article_store.py`, `src/storage/digest_store.py` |
| 1.13 | Write `src/storage/vector_store.py` (Pinecone wrapper: upsert, query, delete) | `src/storage/vector_store.py` |
| 1.14 | Create `.env.example` with all required env vars | `.env.example` |
| 1.15 | Add `.gitignore` | `.gitignore` |

### 1.2 Config Files Detail

**`config/settings.yml`:**
```yaml
pipeline:
  schedule: "09:00"
  timezone: "Asia/Kolkata"
  max_articles_per_source: 20

embedding:
  model: "BAAI/bge-small-en-v1.5"
  dimensions: 384
  chunk_size: 512
  chunk_overlap: 50

vector_store:
  provider: "pinecone"
  index_name: "ai-news-articles"
  top_k: 10
  similarity_threshold: 0.70

llm:
  provider: "groq"
  primary_model: "llama-3.3-70b-versatile"
  fallback_model: "llama-3.1-8b-instant"
  temperature: 0.1
  max_tokens: 2000
  timeout: 30

database:
  provider: "postgresql"
  retention_days: 90
```

**`.env.example`:**
```
GROQ_API_KEY=gsk_...
PINECONE_API_KEY=pc-...
DATABASE_URL=postgresql://user:pass@localhost:5432/ainewspulse
SENDGRID_API_KEY=SG...          # optional
```

### 1.3 PostgreSQL Schema

```sql
-- articles table
CREATE TABLE articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    source_name TEXT NOT NULL,
    category TEXT NOT NULL,
    body_text TEXT,
    body_hash TEXT,
    published_date DATE,
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    is_duplicate BOOLEAN DEFAULT FALSE,
    language TEXT DEFAULT 'en'
);

CREATE INDEX idx_articles_date ON articles(published_date);
CREATE INDEX idx_articles_source ON articles(source_name);
CREATE INDEX idx_articles_category ON articles(category);

-- digests table
CREATE TABLE digests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE UNIQUE NOT NULL,
    highlight_json JSONB,
    sections_json JSONB,
    metadata_json JSONB,
    markdown_content TEXT,
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    pipeline_status TEXT DEFAULT 'pending'
);

CREATE INDEX idx_digests_date ON digests(date);
```

### 1.4 Neon Serverless Postgres Limits
- **Compute Time**: 100 CU-hrs monthly per project
- **Storage**: 0.5 GB of storage per project
- **Scale**: Sizes up to 2 CU (8 GB RAM)

### 1.5 Acceptance Criteria

- [ ] Running `pip install -r requirements.txt` succeeds without errors
- [ ] `config_loader.py` can parse all three YAML config files
- [ ] `vector_store.py` can connect to Pinecone and upsert/query a test vector
- [ ] `article_store.py` and `digest_store.py` can CRUD against PostgreSQL
- [ ] Logger writes structured output to console and file
- [ ] All `__init__.py` files are in place

---

## Phase 2: Ingestion Pipeline

> **Goal:** Scrape articles from all 12 configured sources, clean the content, deduplicate, and store article metadata in PostgreSQL.

### 2.1 Tasks

| # | Task | Files Created / Modified |
|---|---|---|
| 2.1 | Write `src/scrapers/base_scraper.py` — abstract interface | `src/scrapers/base_scraper.py` |
| 2.2 | Write `src/scrapers/robots_checker.py` — robots.txt compliance | `src/scrapers/robots_checker.py` |
| 2.3 | Write `src/scrapers/html_scraper.py` — BeautifulSoup scraper | `src/scrapers/html_scraper.py` |
| 2.4 | Write `src/scrapers/rss_scraper.py` — feedparser-based scraper | `src/scrapers/rss_scraper.py` |
| 2.5 | Write `src/processing/cleaner.py` — HTML strip, unicode normalize, whitespace collapse, language detect, min-length filter | `src/processing/cleaner.py` |
| 2.6 | Write `src/processing/deduplicator.py` — URL, title fuzzy match (rapidfuzz 85%), content hash (SHA-256) | `src/processing/deduplicator.py` |
| 2.7 | Write `src/scrape.py` — orchestrator: load sources → scrape → clean → dedup → store to PostgreSQL | `src/scrape.py` |
| 2.8 | Write `tests/test_scraper.py` — unit tests for scrapers | `tests/test_scraper.py` |
| 2.9 | Write `tests/test_cleaner.py` — unit tests for cleaner | `tests/test_cleaner.py` |
| 2.10 | Write `tests/test_deduplicator.py` — unit tests for dedup | `tests/test_deduplicator.py` |

### 2.2 Scraper Class Hierarchy

```mermaid
classDiagram
    class BaseScraper {
        <<abstract>>
        +name: str
        +url: str
        +category: str
        +rate_limit_ms: int
        +scrape() List~RawArticle~
        +is_allowed() bool
    }

    class HTMLScraper {
        +selectors: dict
        +scrape() List~RawArticle~
    }

    class RSSScraper {
        +feed_url: str
        +scrape() List~RawArticle~
    }

    BaseScraper <|-- HTMLScraper
    BaseScraper <|-- RSSScraper
```

### 2.3 Data Flow

```
sources.yml → For each source:
  ├── robots_checker.is_allowed(url)?
  │     ├── YES → HTMLScraper.scrape() or RSSScraper.scrape()
  │     └── NO  → log warning, skip
  ├── cleaner.clean(raw_articles)
  ├── deduplicator.deduplicate(cleaned_articles)
  └── article_store.bulk_insert(unique_articles)
```

### 2.4 Acceptance Criteria

- [ ] `python src/scrape.py` fetches articles from at least 10 of 12 sources without crashing
- [ ] `robots.txt` is checked before every HTML scrape
- [ ] Rate limiting is enforced (configurable per source via `rate_limit_ms`)
- [ ] Cleaned articles have no HTML tags, normalized unicode, collapsed whitespace
- [ ] Duplicate articles (same URL or >85% title similarity) are flagged
- [ ] Articles are stored in PostgreSQL `articles` table with correct metadata
- [ ] All unit tests pass: `pytest tests/test_scraper.py tests/test_cleaner.py tests/test_deduplicator.py`

---

## Phase 3: Embedding & Vector Store

> **Goal:** Chunk scraped articles (1500 chars), generate 384-dim embeddings with BGE (`BAAI/bge-small-en-v1.5`), and index them in Pinecone.
> 
> *Note on Model Selection:* Both `BAAI/bge-small-en-v1.5` and `bge-large-en-v1.5` share the exact same maximum sequence length of **512 tokens**. Our updated `1500` character chunks (which translate to roughly 375-450 tokens) perfectly maximize this context window without risking truncation. We retain the **small** model over the large model because it offers near state-of-the-art accuracy for standard English news text while running 10x faster locally and requiring significantly less Pinecone storage (384 dimensions vs. 1024 dimensions).

### 3.1 Tasks

| # | Task | Files Created / Modified |
|---|---|---|
| 3.1 | Write `src/processing/chunker.py` — `RecursiveCharacterTextSplitter` (1500 chars, 150 overlap) | `src/processing/chunker.py` |
| 3.2 | Write `src/processing/embedder.py` — BGE `BAAI/bge-small-en-v1.5` wrapper using FlagEmbedding | `src/processing/embedder.py` |
| 3.3 | Extend `src/storage/vector_store.py` — batch upsert with metadata, namespace support, date-based cleanup | `src/storage/vector_store.py` |
| 3.4 | Write `src/embed.py` — orchestrator: load today's articles → chunk → embed → upsert to Pinecone | `src/embed.py` |
| 3.5 | Write `tests/test_chunker.py` | `tests/test_chunker.py` |
| 3.6 | Verify end-to-end: scrape → embed → confirm vectors in Pinecone dashboard | — (manual) |

### 3.2 Embedding Pipeline Flow

```mermaid
flowchart LR
    A["PostgreSQL\n(today's articles)"] --> B["Chunker\n1500 chars / 150 overlap"]
    B --> C["BGE\nBAAI/bge-small-en-v1.5"]
    C --> D["384-dim vectors\n+ metadata"]
    D --> E["Pinecone\nupsert (batch)"]
```

### 3.3 Pinecone Upsert Format

```python
# Each vector upserted to Pinecone
{
    "id": "chunk-uuid",
    "values": [0.012, -0.034, ...],  # 384-dim
    "metadata": {
        "article_id": "article-uuid",
        "source_name": "TechCrunch",
        "category": "funding",
        "title": "Mistral AI raises $800M",
        "url": "https://techcrunch.com/...",
        "published_date": "2026-07-19",
        "chunk_index": 0
    }
}
```

### 3.4 Acceptance Criteria

- [ ] `python src/embed.py` processes today's articles end-to-end
- [ ] Articles are chunked with correct size (1500 characters) and overlap (150 characters)
- [ ] Embeddings are 384-dimensional (matching `BAAI/bge-small-en-v1.5`)
- [ ] Vectors appear in Pinecone with correct metadata
- [ ] Duplicate chunks are not re-embedded (idempotent)
- [ ] Old vectors (>30 days) are cleaned up on each run
- [ ] `pytest tests/test_chunker.py` passes

---

## Phase 4: RAG Digest Generation

> **Goal:** Retrieve today's most relevant articles from Pinecone using category-seeded queries, generate a structured digest via Groq, and format it as Markdown + JSON.

### 4.1 Tasks

| # | Task | Files Created / Modified |
|---|---|---|
| 4.1 | Write `src/rag/prompts.py` — system prompt, user prompt templates, seed queries per category | `src/rag/prompts.py` |
| 4.2 | Write `src/rag/retriever.py` — for each of 6 categories: embed seed query → Pinecone Top-3 → fetch dense semantic matches | `src/rag/retriever.py` |
| 4.3 | Write `src/rag/summarizer.py` — Groq client, `llama-3.3-70b-versatile` call with fallback to `llama-3.1-8b-instant` | `src/rag/summarizer.py` |
| 4.4 | Write `src/rag/formatter.py` — parse LLM output → structured JSON + Markdown file | `src/rag/formatter.py` |
| 4.5 | Write `src/generate_digest.py` — orchestrator: retrieve → summarize → format → save to Neon Postgres + file | `src/generate_digest.py` |
| 4.6 | Write `tests/test_retriever.py` | `tests/test_retriever.py` |
| 4.7 | Write `tests/test_summarizer.py` (mock Groq responses) | `tests/test_summarizer.py` |
| 4.8 | Write `tests/test_formatter.py` | `tests/test_formatter.py` |

### 4.2 Retrieval Flow

```mermaid
flowchart TB
    SEEDS["6 Category Seed Queries"] --> EMBED["Embed with\nBGE (bge-small-en-v1.5)"]
    EMBED --> QUERY["Pinecone query\nTop-3 per category\nnamespace: digest-YYYY-MM-DD"]
    QUERY --> RERANK["Sort by Similarity Score"]
    RERANK --> CONTEXT["Assembled context\nper category"]
    CONTEXT --> LLM["Groq API\nllama-3.3-70b-versatile"]
    LLM --> DIGEST["Structured Digest\n(Markdown + JSON)"]
```

### 4.3 Groq Integration

> **Rate Limit Constraints:** For `llama-3.3-70b-versatile`, Groq enforces strict limits:
> - **RPM (Requests per minute):** 30
> - **RPD (Requests per day):** 1,000
> - **TPM (Tokens per minute):** 12,000
> - **TPD (Tokens per day):** 100,000
> 
> *To respect the 12K TPM limit during our single daily generation, we cap the Pinecone retrieval to **Top-3** chunks per category. (6 categories × 3 chunks × ~450 tokens ≈ 8,100 input tokens). This leaves ample headroom for the LLM's output response without triggering HTTP 429 rate limit exceptions.*

```python
# src/rag/summarizer.py (simplified)
from groq import Groq

client = Groq(api_key=os.environ["GROQ_API_KEY"])

def generate_digest(context_chunks: str, date: str) -> str:
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",      # primary
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT.format(
                    date=date, context_chunks=context_chunks
                )}
            ],
            temperature=0.1,
            max_tokens=2000,
        )
        return response.choices[0].message.content
    except Exception:
        # Fallback to lighter model
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",          # fallback
            messages=[...],
            temperature=0.1,
            max_tokens=2000,
        )
        return response.choices[0].message.content
```

### 4.4 Output Files

Each run produces two files in `data/digests/`:

| File | Example | Content |
|---|---|---|
| `{date}.md` | `2026-07-19.md` | Full Markdown digest for frontend rendering |
| `{date}.json` | `2026-07-19.json` | Structured JSON for API response (see Architecture.md §3.4.3) |

### 4.5 Acceptance Criteria

- [ ] `python src/generate_digest.py` produces a valid digest end-to-end
- [ ] Retriever returns Top-K results per category, filtered to today's date
- [ ] Groq API call succeeds with `llama-3.3-70b-versatile`
- [ ] Fallback to `llama-3.1-8b-instant` works when primary fails
- [ ] Generated digest has correct structure: Highlight + 6 category sections
- [ ] Every bullet point contains a citation link
- [ ] Output saved to Neon `digests` table AND `data/digests/{date}.md` + `.json`
- [ ] Content guardrails enforced (no opinions, no financial advice, no speculation)
- [ ] All unit tests pass

---

## Phase 5: API & Frontend

> **Goal:** Build the FastAPI REST API to serve digests, and a read-only frontend digest viewer with dark mode and archive.

### 5.1 Tasks — API

| # | Task | Files Created / Modified |
|---|---|---|
| 5.1 | Write `src/delivery/api.py` — FastAPI app with 4 endpoints | `src/delivery/api.py` |
| 5.2 | `GET /v1/digest/today` — return today's digest JSON from Neon Postgres | `src/delivery/api.py` |
| 5.3 | `GET /v1/digest/{date}` — return a specific date's digest | `src/delivery/api.py` |
| 5.4 | `GET /v1/digest/archive` — paginated list of available digests | `src/delivery/api.py` |
| 5.5 | `GET /v1/health` — pipeline status, Pinecone connectivity, counts | `src/delivery/api.py` |
| 5.6 | Add CORS middleware, rate limiting | `src/delivery/api.py` |
| 5.7 | Write `tests/test_api.py` | `tests/test_api.py` |

### 5.2 Tasks — Frontend

| # | Task | Files Created / Modified |
|---|---|---|
| 5.8 | Write `frontend/index.html` — Today's digest page (header, highlight hero, category sections, disclaimer, footer) | `frontend/index.html` |
| 5.9 | Write `frontend/archive.html` — Archive browser with date list | `frontend/archive.html` |
| 5.10 | Write `frontend/css/styles.css` — responsive layout, dark mode, collapsible sections, glassmorphism, typography | `frontend/css/styles.css` |
| 5.11 | Write `frontend/js/app.js` — fetch from API, render digest, handle collapsible sections | `frontend/js/app.js` |
| 5.12 | Write `frontend/js/theme.js` — dark/light toggle with `prefers-color-scheme` detection | `frontend/js/theme.js` |

### 5.3 API Endpoints Summary

```mermaid
flowchart LR
    subgraph FastAPI
        A["GET /v1/digest/today"]
        B["GET /v1/digest/{date}"]
        C["GET /v1/digest/archive"]
        D["GET /v1/health"]
    end

    PG["PostgreSQL"] --> A
    PG --> B
    PG --> C
    PC["Pinecone + Pipeline"] --> D
    A --> FE["Frontend"]
    B --> FE
    C --> FE
```

### 5.4 Frontend Pages

#### Today's Digest (`/`)

```
┌──────────────────────────────────────────┐
│  AI News Pulse — Your Daily AI Digest    │  ← Header
│  🌙 Dark Mode Toggle                     │
├──────────────────────────────────────────┤
│  ● Last updated: 19 Jul 2026 09:12 AM   │  ← Status bar
├──────────────────────────────────────────┤
│  ⭐ HIGHLIGHT OF THE DAY                 │
│  ┌────────────────────────────────────┐  │
│  │ Anthropic releases Claude 4.5...   │  │  ← Hero card
│  │ [TechCrunch →]                     │  │
│  └────────────────────────────────────┘  │
├──────────────────────────────────────────┤
│  🚀 LLM & Model Releases          [▼]  │  ← Collapsible
│    • Summary 1... [Source →]             │
│    • Summary 2... [Source →]             │
├──────────────────────────────────────────┤
│  📄 Research Papers                [▼]  │
│    • ...                                 │
├──────────────────────────────────────────┤
│  💰 Startups & Funding             [▼]  │
│    • ...                                 │
├──────────────────────────────────────────┤
│  ⚖️ Policy & Regulation            [▼]  │
├──────────────────────────────────────────┤
│  🔧 Open-Source & Tools            [▼]  │
├──────────────────────────────────────────┤
│  🏢 Industry Applications          [▼]  │
├──────────────────────────────────────────┤
│  ⚠️ Disclaimer: Summaries are AI-gen... │
│  📅 Browse Archive                       │
└──────────────────────────────────────────┘
```

### 5.5 Acceptance Criteria

- [ ] `uvicorn src.delivery.api:app` starts without errors
- [ ] All 4 API endpoints return correct responses
- [ ] CORS is configured to allow frontend domain
- [ ] Frontend fetches and renders today's digest from API
- [ ] Dark mode toggle works (persists via `localStorage`)
- [ ] Category sections are collapsible
- [ ] Archive page lists past digests and navigates to detail
- [ ] Responsive layout works on mobile (≤768px) and desktop
- [ ] Disclaimer is visible on every page
- [ ] Status indicator shows green/yellow/red based on pipeline status
- [ ] `pytest tests/test_api.py` passes

---

## Phase 6: Scheduler, CI/CD & Polish

> **Goal:** Wire everything together with GitHub Actions, add email delivery, implement error handling, write documentation, and finalize testing.

### 6.1 Tasks

| # | Task | Files Created / Modified |
|---|---|---|
| 6.1 | Write `.github/workflows/daily-digest.yml` — cron `30 3 * * *` (9:00 AM IST) + `workflow_dispatch` | `.github/workflows/daily-digest.yml` |
| 6.2 | Write `src/publish.py` — save digest to PostgreSQL, write files to `data/digests/` | `src/publish.py` |
| 6.3 | Write `src/delivery/email_sender.py` — SendGrid/SES email dispatch | `src/delivery/email_sender.py` |
| 6.4 | Write `src/notify.py` — read subscribers.yml, send email with digest | `src/notify.py` |
| 6.5 | Add retry logic with exponential backoff to scraper, Groq client, and Pinecone calls | Multiple files |
| 6.6 | Add pipeline status tracking (JSON status record per run) | `src/publish.py`, `src/delivery/api.py` |
| 6.7 | Implement 30-day TTL cleanup for Pinecone vectors and PostgreSQL articles | `src/storage/vector_store.py`, `src/storage/article_store.py` |
| 6.8 | Write `README.md` with setup, usage, and deployment instructions | `README.md` |
| 6.9 | Finalize and run all tests | `tests/` |
| 6.10 | Manual end-to-end dry run: trigger pipeline → verify digest → verify frontend | — (manual) |

### 6.2 GitHub Actions Workflow

```yaml
name: Daily AI Digest
on:
  schedule:
    - cron: '30 3 * * *'    # 9:00 AM IST (UTC+5:30)
  workflow_dispatch: {}      # Manual trigger

jobs:
  generate-digest:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Step 1 — Scrape articles
        run: python src/scrape.py
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}

      - name: Step 2 — Embed & index
        run: python src/embed.py
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          PINECONE_API_KEY: ${{ secrets.PINECONE_API_KEY }}

      - name: Step 3 — Generate digest
        run: python src/generate_digest.py
        env:
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
          PINECONE_API_KEY: ${{ secrets.PINECONE_API_KEY }}
          DATABASE_URL: ${{ secrets.DATABASE_URL }}

      - name: Step 4 — Publish
        run: python src/publish.py
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}

      - name: Step 5 — Notify (email)
        run: python src/notify.py
        env:
          SENDGRID_API_KEY: ${{ secrets.SENDGRID_API_KEY }}
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

### 6.3 Acceptance Criteria

- [ ] GitHub Actions workflow triggers on schedule and via manual dispatch
- [ ] Full pipeline completes within 15 minutes
- [ ] Pipeline status record is saved after each run
- [ ] Email delivery works (if configured)
- [ ] Retry logic handles transient Groq/Pinecone failures gracefully
- [ ] Fallback from `llama-3.3-70b-versatile` → `llama-3.1-8b-instant` works
- [ ] 30-day cleanup removes old vectors and article records
- [ ] README.md is complete with setup, config, and deployment instructions
- [ ] All tests pass: `pytest tests/ -v`
- [ ] End-to-end dry run succeeds: cron → scrape → embed → generate → publish → frontend renders

---

## Phase Dependency Map

```mermaid
flowchart TB
    P1["Phase 1\nSetup & Infra"] --> P2["Phase 2\nIngestion Pipeline"]
    P1 --> P3["Phase 3\nEmbedding & Vector Store"]
    P2 --> P3
    P3 --> P4["Phase 4\nRAG Digest Generation"]
    P4 --> P5["Phase 5\nAPI & Frontend"]
    P1 --> P5
    P4 --> P6["Phase 6\nScheduler, CI/CD & Polish"]
    P5 --> P6

    style P1 fill:#1a1a2e,stroke:#e94560,color:#fff
    style P2 fill:#16213e,stroke:#0f3460,color:#fff
    style P3 fill:#1a1a2e,stroke:#533483,color:#fff
    style P4 fill:#16213e,stroke:#e94560,color:#fff
    style P5 fill:#0f3460,stroke:#e94560,color:#fff
    style P6 fill:#1a1a2e,stroke:#0f3460,color:#fff
```

---

## Files Created Per Phase — Summary

| Phase | New Files | Count |
|---|---|---|
| **Phase 1** | `requirements.txt`, `config/settings.yml`, `config/sources.yml`, `config/subscribers.yml`, `src/utils/config_loader.py`, `src/utils/logger.py`, `src/utils/date_utils.py`, `src/storage/article_store.py`, `src/storage/digest_store.py`, `src/storage/vector_store.py`, `.env.example`, `.gitignore`, all `__init__.py` | ~15 |
| **Phase 2** | `src/scrapers/base_scraper.py`, `html_scraper.py`, `rss_scraper.py`, `robots_checker.py`, `src/processing/cleaner.py`, `deduplicator.py`, `src/scrape.py`, `tests/test_scraper.py`, `test_cleaner.py`, `test_deduplicator.py` | 10 |
| **Phase 3** | `src/processing/chunker.py`, `embedder.py`, `src/embed.py`, `tests/test_chunker.py` | 4 |
| **Phase 4** | `src/rag/prompts.py`, `retriever.py`, `summarizer.py`, `formatter.py`, `src/generate_digest.py`, `tests/test_retriever.py`, `test_summarizer.py`, `test_formatter.py` | 8 |
| **Phase 5** | `src/delivery/api.py`, `frontend/index.html`, `archive.html`, `css/styles.css`, `js/app.js`, `js/theme.js`, `tests/test_api.py` | 7 |
| **Phase 6** | `.github/workflows/daily-digest.yml`, `src/publish.py`, `src/delivery/email_sender.py`, `src/notify.py`, `README.md` | 5 |
| **Total** | | **~49 files** |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Source website changes HTML structure | High | Scraper breaks for that source | CSS selectors in `sources.yml` are configurable; scraper logs warnings and continues |
| Groq rate limit exhausted | Low | Digest not generated | Single daily run uses ~2K tokens; well within 100K/day limit. Fallback model available. |
| Pinecone free tier limit (100K vectors) | Medium | Can't index new articles | 30-day TTL cleanup keeps count manageable (~200 articles × 5 chunks × 30 days = ~30K vectors) |
| LLM hallucination in digest | Medium | Incorrect news summary | Low temperature (0.1), strict system prompt, citation-required rule, and human spot-checks |
| GitHub Actions downtime | Low | Pipeline doesn't trigger | `workflow_dispatch` for manual trigger; idempotent pipeline can be re-run safely |

---

> **Document Version:** 1.0
> **Created:** 19 Jul 2026
> **Aligned With:** [Architecture.md](file:///c:/Users/Admin/Documents/Article%20reader%20project/Architecture.md) v1.1 | [context.md](file:///c:/Users/Admin/Documents/Article%20reader%20project/context.md)
