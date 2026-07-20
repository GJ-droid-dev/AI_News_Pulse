# AI News Pulse — Architecture Document

> Detailed technical architecture for a fully automated, push-based RAG system that scrapes AI news daily and generates a structured digest — without any user query.

---

## Table of Contents

- [1. System Overview](#1-system-overview)
- [2. High-Level Architecture Diagram](#2-high-level-architecture-diagram)
- [3. Pipeline Stages (Deep Dive)](#3-pipeline-stages-deep-dive)
  - [3.1 Scheduler](#31-scheduler)
  - [3.2 Ingestion Pipeline](#32-ingestion-pipeline)
  - [3.3 Embedding Pipeline](#33-embedding-pipeline)
  - [3.4 Digest Generation (RAG)](#34-digest-generation-rag)
  - [3.5 Delivery Layer](#35-delivery-layer)
  - [3.6 Frontend](#36-frontend)
- [4. Data Flow Diagram](#4-data-flow-diagram)
- [5. Data Models & Schemas](#5-data-models--schemas)
- [6. Technology Stack](#6-technology-stack)
- [7. Directory Structure](#7-directory-structure)
- [8. API Specification](#8-api-specification)
- [9. Deployment Architecture](#9-deployment-architecture)
- [10. Error Handling & Resilience](#10-error-handling--resilience)
- [11. Security & Privacy](#11-security--privacy)
- [12. Monitoring & Observability](#12-monitoring--observability)
- [13. Scalability & Future Considerations](#13-scalability--future-considerations)

---

## 1. System Overview

AI News Pulse is a **zero-touch, push-based** RAG pipeline. There is no user query path. The entire system operates as a scheduled batch job:

```
CRON TRIGGER (9:00 AM) → SCRAPE → CLEAN → EMBED → RETRIEVE → SUMMARIZE → PUBLISH
```

### Key Design Principles

| Principle | Description |
|---|---|
| **Zero-touch** | No manual intervention required. The pipeline runs end-to-end on a cron schedule. |
| **Push, not pull** | The system generates and publishes a digest automatically. Users consume it passively. |
| **Source-grounded** | Every statement in the digest must link back to a scraped source article. |
| **Category-structured** | The digest is organized into 6 predefined categories for scan-ability. |
| **Idempotent** | Re-running the pipeline for the same day produces the same digest (barring new scrapes). |
| **Fail-safe** | Individual source failures do not block the entire pipeline. Partial digests are acceptable. |

---

## 2. High-Level Architecture Diagram

```mermaid
flowchart TB
    subgraph Scheduler["⏰ Scheduler (GitHub Actions)"]
        CRON["Cron Trigger\n9:00 AM IST Daily"]
        GHA["GitHub Actions\nWorkflow Runner"]
        CRON --> GHA
    end

    subgraph Ingestion["📥 Ingestion Pipeline"]
        direction TB
        SCRAPER["Web Scraper\n(BeautifulSoup + Requests / Scrapy)"]
        RSS["RSS Parser\n(feedparser)"]
        NORM["Normalizer\n& Cleaner"]
        DEDUP["Deduplication\nEngine"]
        SCRAPER --> NORM
        RSS --> NORM
        NORM --> DEDUP
    end

    subgraph Embedding["🧮 Embedding Pipeline"]
        direction TB
        CHUNKER["Text Chunker\n(RecursiveCharacterTextSplitter)"]
        EMBEDDER["Embedding Model\n(BGE — BAAI/bge-small-en-v1.5\nvia FlagEmbedding)"]
        INDEXER["Vector Indexer"]
        CHUNKER --> EMBEDDER --> INDEXER
    end

    subgraph VectorDB["📦 Vector Store"]
        PINECONE["Pinecone\n(Serverless Index)"]
    end

    subgraph DigestGen["🤖 Digest Generation (RAG)"]
        direction TB
        RETRIEVER["Semantic Retriever\n(Top-K per category)"]
        CATEGORIZER["Category Classifier\n(LLM-based or rule-based)"]
        SUMMARIZER["LLM Summarizer\n(Groq — llama-3.3-70b-versatile)"]
        FORMATTER["Digest Formatter\n(Markdown + JSON)"]
        RETRIEVER --> CATEGORIZER --> SUMMARIZER --> FORMATTER
    end

    subgraph Storage["💾 Persistent Storage"]
        DIGEST_DB["Digest Store\n(PostgreSQL)"]
        ARTICLE_DB["Article Metadata\nStore"]
    end

    subgraph Delivery["📤 Delivery Layer"]
        API["FastAPI\nREST API"]
        EMAIL["Email Service\n(SendGrid / SES)\n— Optional"]
    end

    subgraph Frontend["💻 Frontend (Read-Only)"]
        UI["Digest Viewer\nToday + Archive\n(Vanilla JS / React)"]
    end

    GHA --> SCRAPER
    GHA --> RSS
    DEDUP --> CHUNKER
    DEDUP --> ARTICLE_DB
    INDEXER --> PINECONE
    PINECONE --> RETRIEVER
    FORMATTER --> DIGEST_DB
    FORMATTER --> API
    FORMATTER --> EMAIL
    API --> UI
    DIGEST_DB --> API

    style Scheduler fill:#1a1a2e,stroke:#e94560,color:#fff
    style Ingestion fill:#16213e,stroke:#0f3460,color:#fff
    style Embedding fill:#1a1a2e,stroke:#533483,color:#fff
    style VectorDB fill:#0f3460,stroke:#e94560,color:#fff
    style DigestGen fill:#16213e,stroke:#e94560,color:#fff
    style Storage fill:#1a1a2e,stroke:#0f3460,color:#fff
    style Delivery fill:#16213e,stroke:#533483,color:#fff
    style Frontend fill:#0f3460,stroke:#e94560,color:#fff
```

---

## 3. Pipeline Stages (Deep Dive)

### 3.1 Scheduler

The scheduler is the entry point. It triggers the entire pipeline at a fixed time every day.

| Property | Value |
|---|---|
| **Platform** | GitHub Actions |
| **Trigger** | Cron schedule: `0 3 * * *` (9:00 AM IST = 3:30 AM UTC) |
| **Workflow File** | `.github/workflows/daily-digest.yml` |
| **Fallback** | Manual dispatch via `workflow_dispatch` for on-demand runs |
| **Timeout** | 15 minutes max per run |

#### Workflow Steps (Sequential)

```mermaid
flowchart LR
    A["1. Checkout\nRepository"] --> B["2. Setup Python\nEnvironment"]
    B --> C["3. Install\nDependencies"]
    C --> D["4. Run Scraper\n(scrape.py)"]
    D --> E["5. Run Embedder\n(embed.py)"]
    E --> F["6. Run Digest\nGenerator\n(generate_digest.py)"]
    F --> G["7. Publish Digest\n(publish.py)"]
    G --> H["8. Send\nNotifications\n(notify.py)"]
```

#### Example GitHub Actions YAML

```yaml
name: Daily AI Digest
on:
  schedule:
    - cron: '30 3 * * *'  # 9:00 AM IST
  workflow_dispatch: {}     # Manual trigger

jobs:
  generate-digest:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python src/scrape.py
        env:
          SCRAPE_DATE: ${{ github.event.inputs.date || '' }}
      - run: python src/embed.py
      - run: python src/generate_digest.py
        env:
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
      - run: python src/publish.py
      - run: python src/notify.py
        env:
          SENDGRID_API_KEY: ${{ secrets.SENDGRID_API_KEY }}
```

---

### 3.2 Ingestion Pipeline

The ingestion pipeline is responsible for fetching raw content from 12 configured sources.

#### 3.2.1 Source Registry

Sources are defined in a YAML configuration file (`config/sources.yml`):

```yaml
sources:
  - name: "MIT Technology Review — AI"
    url: "https://www.technologyreview.com/topic/artificial-intelligence/"
    type: "html"
    scraper: "beautifulsoup"
    selectors:
      article_list: "div.feed__item"
      title: "h3 a"
      link: "h3 a[href]"
      summary: "p.feed__item__description"
    category: "research_industry"
    rate_limit_ms: 2000

  - name: "arXiv — cs.AI"
    url: "https://arxiv.org/list/cs.AI/recent"
    type: "rss"
    feed_url: "https://rss.arxiv.org/rss/cs.AI"
    category: "research_papers"
    rate_limit_ms: 1000
```

#### 3.2.2 Scraping Strategy

```mermaid
flowchart TB
    START["Load sources.yml"] --> LOOP["For each source"]
    LOOP --> CHECK_TYPE{"Source type?"}
    CHECK_TYPE -->|"HTML"| BS["BeautifulSoup\n+ Requests"]
    CHECK_TYPE -->|"RSS"| FP["feedparser"]
    CHECK_TYPE -->|"API"| API_CALL["HTTP API Call"]

    BS --> ROBOTS["Check robots.txt\n(urllib.robotparser)"]
    ROBOTS -->|"Allowed"| FETCH["Fetch Page\n(with rate limit)"]
    ROBOTS -->|"Blocked"| SKIP["Skip Source\n(log warning)"]
    FETCH --> EXTRACT["Extract Articles\n(title, URL, body, date)"]

    FP --> PARSE["Parse Feed Entries"]
    API_CALL --> JSON_PARSE["Parse JSON Response"]

    EXTRACT --> RAW_STORE["Raw Article Object"]
    PARSE --> RAW_STORE
    JSON_PARSE --> RAW_STORE

    RAW_STORE --> NEXT{"More sources?"}
    NEXT -->|"Yes"| LOOP
    NEXT -->|"No"| DONE["Return all raw articles"]
```

#### 3.2.3 Normalization & Cleaning

After scraping, each raw article passes through a cleaning pipeline:

| Step | Operation | Tool/Library |
|---|---|---|
| 1 | Strip HTML tags | `BeautifulSoup.get_text()` |
| 2 | Remove ads, nav, footers | CSS selector exclusion lists |
| 3 | Unicode normalization | `unicodedata.normalize('NFKC', text)` |
| 4 | Whitespace collapse | Regex: `re.sub(r'\s+', ' ', text)` |
| 5 | Date extraction & normalization | `dateutil.parser` → ISO 8601 |
| 6 | Language detection | `langdetect` — keep English only |
| 7 | Minimum length filter | Discard articles < 100 chars |

#### 3.2.4 Deduplication

Prevents the same story from multiple sources from being embedded multiple times.

| Method | How It Works |
|---|---|
| **URL-based** | Exact match on canonical URL (after stripping query params) |
| **Title similarity** | Fuzzy match using `rapidfuzz` with a threshold of 85% similarity |
| **Content hash** | SHA-256 hash of the first 500 characters of cleaned body text |

When duplicates are detected, the **earliest-published** version is kept and others are marked as `duplicate` in the article metadata store.

---

### 3.3 Embedding Pipeline

Converts cleaned article text into vector embeddings for semantic retrieval.

#### 3.3.1 Chunking Strategy

```mermaid
flowchart LR
    ARTICLE["Cleaned Article\n(full text)"] --> SPLITTER["RecursiveCharacterTextSplitter"]
    SPLITTER --> CHUNKS["Chunks\n(512 tokens each,\n50 token overlap)"]
    CHUNKS --> METADATA["Attach Metadata\n(source, URL, date, category)"]
```

| Parameter | Value | Rationale |
|---|---|---|
| **Chunk size** | 512 tokens | Balances context richness with embedding model limits |
| **Chunk overlap** | 50 tokens | Preserves sentence continuity at chunk boundaries |
| **Splitter** | `RecursiveCharacterTextSplitter` | Splits on `\n\n` → `\n` → `. ` → ` ` for natural breaks |

#### 3.3.2 Embedding Model

| Option | Model | Dimensions | Cost |
|---|---|---|---|
| **Primary** | `BAAI/bge-small-en-v1.5` (BGE via FlagEmbedding) | 384 | Free (local) |
| **Alternative** | `BAAI/bge-base-en-v1.5` (BGE via FlagEmbedding) | 768 | Free (local) |

> **Note:** BGE (BAAI General Embedding) models consistently rank among the top embedding models on the MTEB leaderboard. Using `FlagEmbedding` keeps the embedding pipeline fully local and free. No external API calls are needed for embedding generation.

#### 3.3.3 Vector Store Configuration

| Property | Value |
|---|---|
| **Store** | Pinecone (Serverless) |
| **Index name** | `ai-news-articles` |
| **Cloud / Region** | AWS `us-east-1` (Pinecone free tier) |
| **Dimensions** | 384 (matching `BAAI/bge-small-en-v1.5` output) |
| **Distance metric** | Cosine similarity |
| **Metadata indexed** | `source_name`, `category`, `published_date`, `url`, `title` |
| **Namespace** | Date-based: `digest-2026-07-19` |
| **TTL Policy** | Articles older than 30 days are deleted via scheduled cleanup |

```mermaid
erDiagram
    CHUNK {
        string id PK "uuid4"
        string text "chunk content"
        float[] embedding "vector (384-dim, BGE)"
        string article_id FK "parent article"
        string source_name "e.g. TechCrunch"
        string category "e.g. funding"
        string url "original article URL"
        string title "article title"
        date published_date "article date"
        datetime ingested_at "timestamp"
    }
```

---

### 3.4 Digest Generation (RAG)

This is the core RAG stage. It retrieves today's most relevant articles and uses an LLM to generate the structured daily digest.

#### 3.4.1 Retrieval Strategy

Unlike traditional RAG (user query → retrieve → generate), this system uses **category-seeded retrieval**:

```mermaid
flowchart TB
    CATEGORIES["6 Predefined Categories"] --> SEED["Generate Seed Queries\nper Category"]
    SEED --> EMBED_Q["Embed Seed Queries"]
    EMBED_Q --> SEARCH["Vector Similarity Search\n(Top-K per category,\nfiltered by date = today)"]
    SEARCH --> RANK["Re-rank by\nrecency + relevance"]
    RANK --> CONTEXT["Assemble Context\nper Category"]
```

**Seed queries** are predefined prompts designed to retrieve relevant articles for each category:

| Category | Seed Query |
|---|---|
| 🚀 LLM & Model Releases | "New large language model released, LLM benchmark, model update, GPT Claude Gemini Llama launch" |
| 📄 Research Papers | "AI research paper published, machine learning breakthrough, novel approach, state of the art" |
| 💰 Startups & Funding | "AI startup funding round, AI company acquisition, seed series venture capital artificial intelligence" |
| ⚖️ Policy & Regulation | "AI regulation policy government, AI safety legislation, AI act compliance, AI governance" |
| 🔧 Open-Source & Tools | "Open source AI tool released, new ML framework library, HuggingFace model release, developer tools" |
| 🏢 Industry Applications | "Enterprise AI deployment, AI product launch, AI partnership, AI integration business" |

**Retrieval parameters:**

| Parameter | Value |
|---|---|
| Top-K per category | 10 chunks |
| Date filter | `published_date >= today - 24h` |
| Similarity threshold | Cosine similarity ≥ 0.70 |
| Re-ranking | By `published_date` (newest first), then by similarity score |

#### 3.4.2 LLM Summarization

The retrieved chunks are passed to the LLM with a carefully engineered system prompt:

```
SYSTEM PROMPT:
You are AI News Pulse, an automated AI news digest generator.
Your task is to produce a structured daily digest from the provided article chunks.

RULES:
1. Group summaries under these exact category headers:
   🚀 LLM & Model Releases | 📄 Research Papers | 💰 Startups & Funding
   ⚖️ Policy & Regulation | 🔧 Open-Source & Tools | 🏢 Industry Applications
2. Write 3-5 bullet points per category. Each bullet must be 1-2 sentences max.
3. EVERY bullet must end with a citation: [Source Name](URL)
4. Select the single most impactful story as "⭐ Highlight of the Day" at the top.
5. Omit any category with zero relevant articles.
6. NEVER include: financial advice, subjective rankings, speculation, or opinions.
7. NEVER reproduce full article text. Summarize only.
8. Tone: Professional, neutral, factual.

USER PROMPT:
Today's date: {date}
Retrieved article chunks (grouped by category):
{context_chunks}

Generate the daily digest.
```

| LLM Config | Value |
|---|---|
| **Provider** | Groq (ultra-low latency inference) |
| **Primary Model** | `llama-3.3-70b-versatile` — 12K tokens/min, 1K req/day, 100K tokens/day |
| **Fallback Model** | `llama-3.1-8b-instant` — 6K tokens/min, 14.4K req/day, 500K tokens/day |
| **Temperature** | 0.1 (near-deterministic for factual output) |
| **Max tokens** | 2000 |
| **Timeout** | 30 seconds (Groq is significantly faster than cloud LLMs) |

> **Why Groq?** Groq's LPU inference engine provides sub-second token generation, making the digest generation step extremely fast. The free tier is sufficient for a once-daily pipeline run.

#### Available Groq Models Reference

| Model | Req/Min | Req/Day | Tokens/Min | Tokens/Day |
|---|---|---|---|---|
| `llama-3.3-70b-versatile` ⭐ | 30 | 1K | 12K | 100K |
| `llama-3.1-8b-instant` ⭐ | 30 | 14.4K | 6K | 500K |
| `groq/compound` | 30 | 250 | 70K | No limit |
| `groq/compound-mini` | 30 | 250 | 70K | No limit |
| `qwen/qwen3.6-27b` | 30 | 1K | 8K | 200K |
| `openai/gpt-oss-120b` | 30 | 1K | 8K | 200K |

#### 3.4.3 Digest Formatter

The LLM output is post-processed into two formats:

| Format | Use Case | Storage |
|---|---|---|
| **Markdown** | Frontend rendering, email body | `digests/{date}.md` |
| **JSON** | API response, programmatic access | `digests/{date}.json` |

**JSON Schema:**

```json
{
  "date": "2026-07-19",
  "generated_at": "2026-07-19T09:12:34Z",
  "highlight": {
    "title": "Anthropic releases Claude 4.5 with 2M context window",
    "summary": "Anthropic announced Claude 4.5, featuring a 2M token context...",
    "source": "TechCrunch",
    "url": "https://techcrunch.com/...",
    "category": "llm_releases"
  },
  "sections": [
    {
      "category": "llm_releases",
      "emoji": "🚀",
      "label": "LLM & Model Releases",
      "items": [
        {
          "summary": "Anthropic released Claude 4.5 with a 2M token context window...",
          "source": "TechCrunch",
          "url": "https://techcrunch.com/...",
          "published_date": "2026-07-19"
        }
      ]
    }
  ],
  "metadata": {
    "sources_scraped": 12,
    "articles_ingested": 87,
    "articles_deduplicated": 14,
    "chunks_embedded": 342,
    "generation_model": "llama-3.3-70b-versatile",
    "generation_provider": "groq",
    "pipeline_duration_seconds": 487
  }
}
```

---

### 3.5 Delivery Layer

#### 3.5.1 REST API (FastAPI)

The API serves the pre-generated digest. It does **not** trigger any LLM calls — it simply reads from the digest store.

```mermaid
flowchart LR
    subgraph FastAPI["FastAPI Application"]
        EP1["GET /digest/today"]
        EP2["GET /digest/{date}"]
        EP3["GET /digest/archive"]
        EP4["GET /health"]
    end

    DB["Digest Store\n(PostgreSQL)"] --> EP1
    DB --> EP2
    DB --> EP3
    PIPELINE["Pipeline Status"] --> EP4
```

#### 3.5.2 Email Delivery (Optional)

| Channel | Implementation | Trigger |
|---|---|---|
| **Email** | SendGrid / AWS SES | Post-digest-generation step in GitHub Actions |

Subscribers are managed via a simple config file (`config/subscribers.yml`):

```yaml
email:
  enabled: false
  provider: "sendgrid"
  recipients:
    - "team@example.com"
```

---

### 3.6 Frontend

The frontend is a **read-only digest viewer** — no search bar, no query input, no chat interface.

#### 3.6.1 Pages

| Page | Route | Description |
|---|---|---|
| **Today's Digest** | `/` | Displays the latest daily digest with Highlight of the Day and category sections |
| **Archive** | `/archive` | Calendar/list view of past digests with date picker |
| **Digest Detail** | `/digest/{date}` | View a specific day's digest |

#### 3.6.2 Component Hierarchy

```mermaid
flowchart TB
    APP["App"] --> HEADER["Header\n'AI News Pulse — Your Daily AI Digest'"]
    APP --> STATUS["Status Bar\n'Last updated: 19 Jul 2026 09:12 AM'"]
    APP --> HIGHLIGHT["⭐ Highlight of the Day\n(Hero card)"]
    APP --> SECTIONS["Category Sections\n(Collapsible)"]
    APP --> DISCLAIMER["Disclaimer Banner"]
    APP --> FOOTER["Footer"]

    SECTIONS --> S1["🚀 LLM & Model Releases"]
    SECTIONS --> S2["📄 Research Papers"]
    SECTIONS --> S3["💰 Startups & Funding"]
    SECTIONS --> S4["⚖️ Policy & Regulation"]
    SECTIONS --> S5["🔧 Open-Source & Tools"]
    SECTIONS --> S6["🏢 Industry Applications"]

    S1 --> ITEMS["Digest Items\n(bullet + citation link)"]
```

#### 3.6.3 UI Requirements

| Feature | Details |
|---|---|
| **Responsive** | Mobile-first CSS Grid / Flexbox layout |
| **Dark mode** | Toggle with `prefers-color-scheme` detection + manual override |
| **Collapsible sections** | Click-to-expand category groups |
| **Archive calendar** | Date picker or scrollable list of past dates |
| **Status indicator** | Green/yellow/red badge based on last pipeline run status |
| **Disclaimer** | Persistent banner at bottom of every page |

---

## 4. Data Flow Diagram

End-to-end data flow from cron trigger to user-visible digest:

```mermaid
sequenceDiagram
    participant CRON as ⏰ Cron (9:00 AM)
    participant GHA as GitHub Actions
    participant SCRAPER as Scraper
    participant SOURCES as 12 AI Sources
    participant CLEANER as Normalizer
    participant DEDUP as Deduplicator
    participant CHUNKER as Chunker
    participant EMBEDDER as Embedder
    participant VECTOR as Pinecone
    participant RETRIEVER as Retriever
    participant LLM as Groq LLM
    participant FORMATTER as Formatter
    participant DB as Digest Store
    participant API as FastAPI
    participant UI as Frontend

    CRON->>GHA: Trigger workflow
    GHA->>SCRAPER: Run scrape.py

    loop For each of 12 sources
        SCRAPER->>SOURCES: Fetch articles (HTTP)
        SOURCES-->>SCRAPER: Raw HTML / RSS
    end

    SCRAPER->>CLEANER: Pass raw articles
    CLEANER->>DEDUP: Pass cleaned articles
    DEDUP->>CHUNKER: Pass unique articles

    CHUNKER->>EMBEDDER: Pass text chunks
    EMBEDDER->>VECTOR: Store embeddings

    GHA->>RETRIEVER: Run generate_digest.py
    RETRIEVER->>VECTOR: Query (6 seed queries, date filter)
    VECTOR-->>RETRIEVER: Top-K chunks per category

    RETRIEVER->>LLM: Context + system prompt
    LLM-->>FORMATTER: Generated digest text

    FORMATTER->>DB: Save digest (MD + JSON)
    FORMATTER->>API: Notify new digest available

    UI->>API: GET /digest/today
    API-->>UI: Digest JSON
    UI->>UI: Render digest
```

---

## 5. Data Models & Schemas

### 5.1 Article (Metadata Store)

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `title` | String | Article title |
| `url` | String | Canonical URL (unique) |
| `source_name` | String | e.g., "TechCrunch" |
| `category` | Enum | One of the 6 predefined categories |
| `body_text` | Text | Cleaned article body |
| `body_hash` | String | SHA-256 of first 500 chars |
| `published_date` | Date | Article publication date |
| `scraped_at` | DateTime | When we scraped it |
| `is_duplicate` | Boolean | Flagged by dedup engine |
| `language` | String | Detected language code |

### 5.2 Chunk (Vector Store)

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `article_id` | UUID (FK) | Parent article |
| `text` | String | Chunk content |
| `embedding` | Float[384] | Vector embedding (BAAI/bge-small-en-v1.5) |
| `chunk_index` | Integer | Position within article |
| `source_name` | String | Denormalized for fast filtering |
| `category` | Enum | Denormalized |
| `published_date` | Date | Denormalized |
| `url` | String | Denormalized |

### 5.3 Digest (Digest Store)

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `date` | Date (unique) | Digest date |
| `highlight_json` | JSON | Highlight of the Day object |
| `sections_json` | JSON | Array of category sections |
| `metadata_json` | JSON | Pipeline stats |
| `markdown_content` | Text | Full digest as Markdown |
| `generated_at` | DateTime | When the LLM generated it |
| `pipeline_status` | Enum | `success`, `partial`, `failed` |

---

## 6. Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Scheduler** | GitHub Actions (cron) | Daily pipeline trigger |
| **Language** | Python 3.11+ | All backend logic |
| **Web Scraping** | `BeautifulSoup4`, `requests`, `feedparser` | HTML parsing, RSS parsing |
| **Scraping Framework** | Scrapy (optional, for scale) | Advanced crawling with middleware |
| **Text Processing** | `langchain.text_splitter` | Chunking with overlap |
| **Embeddings** | BGE `BAAI/bge-small-en-v1.5` (via FlagEmbedding) | Text → 384-dim vector (local, free) |
| **Vector Store** | Pinecone (Serverless) | Embedding storage + similarity search |
| **LLM** | Groq — `llama-3.3-70b-versatile` / `llama-3.1-8b-instant` | Digest summarization (ultra-low latency) |
| **API Framework** | FastAPI | REST API for serving digests |
| **Database** | Neon Serverless Postgres | Article metadata + digest storage |
| **Frontend** | Vanilla JS + HTML + CSS (or React) | Read-only digest viewer |
| **Email** | SendGrid / AWS SES | Optional email delivery |
| **CI/CD** | GitHub Actions | Automated pipeline execution |
| **Monitoring** | Python `logging` + GitHub Actions logs | Pipeline observability |
| **Deduplication** | `rapidfuzz`, `hashlib` | Fuzzy + hash-based dedup |

### Key Python Dependencies

```
requirements.txt
─────────────────
beautifulsoup4>=4.12
requests>=2.31
feedparser>=6.0
scrapy>=2.11          # optional
langchain>=0.2
groq>=0.9
FlagEmbedding>=1.2
pinecone>=5.0
fastapi>=0.111
uvicorn>=0.30
pydantic>=2.7
psycopg2-binary>=2.9
python-dateutil>=2.9
rapidfuzz>=3.9
langdetect>=1.0
pyyaml>=6.0
```

---

## 7. Directory Structure

```
ai-news-pulse/
├── .github/
│   └── workflows/
│       └── daily-digest.yml          # Cron-triggered pipeline
│
├── config/
│   ├── sources.yml                   # Source registry (URLs, selectors, categories)
│   ├── subscribers.yml               # Email subscriber config
│   └── settings.yml                  # Global settings (chunk size, top-K, model, etc.)
│
├── src/
│   ├── scrape.py                     # Entry point: fetch articles from all sources
│   ├── embed.py                      # Entry point: chunk + embed + index
│   ├── generate_digest.py            # Entry point: retrieve + summarize + format
│   ├── publish.py                    # Entry point: save digest + update API
│   ├── notify.py                     # Entry point: send email notifications
│   │
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── base_scraper.py           # Abstract base class for scrapers
│   │   ├── html_scraper.py           # BeautifulSoup-based HTML scraper
│   │   ├── rss_scraper.py            # feedparser-based RSS scraper
│   │   └── robots_checker.py         # robots.txt compliance checker
│   │
│   ├── processing/
│   │   ├── __init__.py
│   │   ├── cleaner.py                # HTML stripping, normalization
│   │   ├── deduplicator.py           # URL, title, hash-based dedup
│   │   ├── chunker.py                # Text splitting with overlap
│   │   └── embedder.py               # Embedding generation
│   │
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── retriever.py              # Category-seeded vector retrieval
│   │   ├── summarizer.py             # LLM prompt + generation
│   │   ├── formatter.py              # Markdown + JSON output
│   │   └── prompts.py                # System/user prompt templates
│   │
│   ├── delivery/
│   │   ├── __init__.py
│   │   ├── api.py                    # FastAPI app definition
│   │   └── email_sender.py           # SendGrid / SES integration
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── article_store.py          # CRUD for article metadata
│   │   ├── digest_store.py           # CRUD for daily digests (PostgreSQL)
│   │   └── vector_store.py           # Pinecone wrapper
│   │
│   └── utils/
│       ├── __init__.py
│       ├── config_loader.py          # YAML config parser
│       ├── date_utils.py             # Date normalization helpers
│       └── logger.py                 # Structured logging setup
│
├── frontend/
│   ├── index.html                    # Main digest viewer page
│   ├── archive.html                  # Archive browser page
│   ├── css/
│   │   └── styles.css                # Dark mode, responsive layout
│   └── js/
│       ├── app.js                    # Fetch digest from API, render
│       └── theme.js                  # Dark mode toggle
│
├── data/
│   ├── digests/                      # Generated digest files (MD + JSON)
│   └── raw/                          # Raw scraped HTML (temporary)
│
├── tests/
│   ├── test_scraper.py
│   ├── test_cleaner.py
│   ├── test_deduplicator.py
│   ├── test_chunker.py
│   ├── test_retriever.py
│   ├── test_summarizer.py
│   ├── test_formatter.py
│   └── test_api.py
│
├── requirements.txt
├── README.md
├── Architecture.md                   # ← This document
└── context.md                        # Project context & requirements
```

---

## 8. API Specification

### Base URL

```
Production:  https://api.ainewspulse.com/v1
Development: http://localhost:8000/v1
```

### Endpoints

#### `GET /v1/digest/today`

Returns today's digest.

**Response (200):**
```json
{
  "date": "2026-07-19",
  "highlight": { ... },
  "sections": [ ... ],
  "metadata": { ... }
}
```

**Response (404):**
```json
{
  "error": "No digest available for today. Pipeline may not have run yet."
}
```

---

#### `GET /v1/digest/{date}`

Returns the digest for a specific date.

| Parameter | Type | Format | Required |
|---|---|---|---|
| `date` | Path | `YYYY-MM-DD` | Yes |

**Response (200):** Same schema as `/digest/today`

**Response (404):**
```json
{
  "error": "No digest found for 2026-07-15."
}
```

---

#### `GET /v1/digest/archive`

Returns a list of available digest dates.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `limit` | Query | 30 | Max results to return |
| `offset` | Query | 0 | Pagination offset |

**Response (200):**
```json
{
  "total": 45,
  "dates": [
    { "date": "2026-07-19", "status": "success", "article_count": 87 },
    { "date": "2026-07-18", "status": "success", "article_count": 63 },
    { "date": "2026-07-17", "status": "partial", "article_count": 41 }
  ]
}
```

---

#### `GET /v1/health`

Returns pipeline and service health.

**Response (200):**
```json
{
  "status": "healthy",
  "last_scrape": "2026-07-19T03:30:12Z",
  "last_digest": "2026-07-19T03:42:58Z",
  "vector_store": "connected",
  "article_count": 4521,
  "digest_count": 45
}
```

---

## 9. Deployment Architecture

### Option A: Serverless (Recommended for v1)

```mermaid
flowchart LR
    GHA["GitHub Actions\n(Scheduler + Pipeline)"] --> PINECONE["Pinecone\n(Serverless Index)"]
    GHA --> RENDER["Render / Vercel\n(FastAPI + Frontend)"]
    RENDER --> PG["PostgreSQL\n(Supabase / Neon)"]
    RENDER --> USERS["Users"]
    GHA -.->|"Optional"| SG["SendGrid\n(Email)"]
```

| Component | Platform | Cost |
|---|---|---|
| Pipeline execution | GitHub Actions (free tier: 2000 min/month) | Free |
| API + Frontend hosting | Render / Vercel / Railway | Free tier available |
| Vector store | Pinecone Serverless (free tier: 100K vectors) | Free |
| Database | PostgreSQL via Supabase / Neon (free tier) | Free |
| LLM API | Groq (free tier: 100K tokens/day for 70b-versatile) | Free |
| Embeddings | BGE via FlagEmbedding (local, runs in pipeline) | Free |

### Option B: Self-Hosted (Docker Compose)

```yaml
# docker-compose.yml
services:
  api:
    build: .
    ports: ["8000:8000"]
    volumes:
      - ./data:/app/data
    environment:
      - GROQ_API_KEY=${GROQ_API_KEY}
      - PINECONE_API_KEY=${PINECONE_API_KEY}
      - DATABASE_URL=postgresql://user:pass@postgres:5432/ainewspulse

  frontend:
    image: nginx:alpine
    ports: ["80:80"]
    volumes:
      - ./frontend:/usr/share/nginx/html

  postgres:
    image: postgres:16-alpine
    ports: ["5432:5432"]
    environment:
      - POSTGRES_DB=ainewspulse
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - pg_data:/var/lib/postgresql/data

volumes:
  pg_data:
```

---

## 10. Error Handling & Resilience

### 10.1 Failure Modes & Recovery

| Failure | Impact | Recovery Strategy |
|---|---|---|
| Single source scrape fails | Missing articles from that source | Log warning, continue with remaining sources. Digest is marked `partial`. |
| All scrapes fail | No new articles | Skip digest generation. Publish a "No new articles today" placeholder. Alert via email. |
| Embedding fails (local) | Chunks not embedded | Since BGE (FlagEmbedding) runs locally, failures are rare. Retry the batch. If OOM, reduce batch size. |
| Groq API down | Digest not generated | Retry 3× with backoff. Fall back from `llama-3.3-70b-versatile` to `llama-3.1-8b-instant`. If both fail, publish raw headlines without summaries. |
| Groq rate limit hit | 429 response | Back off and retry. For daily pipeline (single run), rate limits are unlikely to be hit. |
| Pinecone unreachable | Retrieval fails | Retry 3×. If persistent, fall back to keyword-based retrieval on PostgreSQL article metadata store. |
| GitHub Actions timeout | Pipeline incomplete | Workflow is configured to re-run on failure (`continue-on-error` + `if: failure()`). |

### 10.2 Retry Policy

```python
RETRY_CONFIG = {
    "max_retries": 3,
    "backoff_base": 2,       # seconds
    "backoff_factor": 2,     # exponential: 2s, 4s, 8s
    "max_backoff": 30,       # seconds
    "retryable_errors": [
        ConnectionError,
        TimeoutError,
        HTTPError(status_code=429),  # Rate limited
        HTTPError(status_code=500),  # Server error
        HTTPError(status_code=503),  # Service unavailable
    ]
}
```

### 10.3 Pipeline Status Tracking

Each pipeline run produces a status record:

```json
{
  "run_id": "abc123",
  "date": "2026-07-19",
  "started_at": "2026-07-19T03:30:00Z",
  "completed_at": "2026-07-19T03:42:58Z",
  "status": "partial",
  "stages": {
    "scrape":   { "status": "partial", "sources_ok": 11, "sources_failed": 1, "error": "timeout on arstechnica.com" },
    "embed":    { "status": "success", "chunks_embedded": 342 },
    "generate": { "status": "success", "provider": "groq", "model": "llama-3.3-70b-versatile", "tokens_used": 1847 },
    "publish":  { "status": "success" },
    "notify":   { "status": "success", "channels": ["email"] }
  }
}
```

---

## 11. Security & Privacy

| Concern | Mitigation |
|---|---|
| **API keys in code** | All secrets stored in GitHub Actions secrets / environment variables. Never committed. |
| **Scraping ethics** | `robots.txt` checked before every scrape. Rate limits enforced per source. |
| **Copyright** | Only summaries are stored. Full article text is discarded after chunking. |
| **User privacy** | No PII collected. No user accounts. No cookies. No tracking. |
| **API security** | Rate limiting via FastAPI middleware. CORS restricted to frontend domain. |
| **Data retention** | Raw scraped HTML deleted after processing. Article metadata retained for 90 days. Digests retained indefinitely. |

---

## 12. Monitoring & Observability

| What | How | Where |
|---|---|---|
| Pipeline success/failure | GitHub Actions run status | GitHub UI + email notification |
| Scrape success rate | Logged per source in pipeline status | `data/logs/pipeline_{date}.json` |
| LLM token usage | Tracked in digest metadata | `metadata.generation_tokens_used` |
| API uptime | `/health` endpoint polled externally | UptimeRobot / similar (free tier) |
| Digest quality | Manual spot-check (weekly) | Team review |
| Vector store size | Tracked in `/health` response | `article_count` field |

### Logging Strategy

```python
# Structured logging with Python's built-in logging
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.FileHandler(f'data/logs/pipeline_{date}.log'),
        logging.StreamHandler()  # Also print to GitHub Actions console
    ]
)
```

---

## 13. Scalability & Future Considerations

### Near-Term (v1.1)

| Feature | Description |
|---|---|
| **Subscriber management** | Simple web form to subscribe via email for daily digest delivery |
| **Weekly recap** | Auto-generated weekly summary aggregating the top stories from 7 daily digests |
| **Source health dashboard** | Track which sources are reliably scrapable and which frequently fail |

### Medium-Term (v2.0)

| Feature | Description |
|---|---|
| **User preferences** | Allow users to select which categories they care about |
| **Multi-language support** | Translate digest into Spanish, Mandarin, Hindi |
| **Trend detection** | Track how topics evolve over weeks/months using embedding cluster analysis |
| **Custom sources** | Allow users to add their own RSS feeds or blog URLs |

### Long-Term (v3.0)

| Feature | Description |
|---|---|
| **Interactive Q&A layer** | Add an optional query interface on top of the existing digest (hybrid push + pull) |
| **Audio digest** | Generate a 5-minute podcast-style audio summary using TTS |
| **Mobile app** | Push notifications with daily digest via native iOS/Android app |

---

> **Document Version:** 1.1  
> **Last Updated:** 19 Jul 2026  
> **Aligned With:** [context.md](file:///c:/Users/Admin/Documents/Article%20reader%20project/context.md)
