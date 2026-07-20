---
trigger: always_on
---

# AI News Pulse — Coding & Architectural Conventions

> **CRITICAL INSTRUCTION FOR AI AGENTS:** You must read and adhere to these conventions before writing any code or making structural changes to the AI News Pulse repository. 

---

## 1. Naming Conventions

### Python
- **Variables & Functions:** `snake_case` (e.g., `generate_digest`, `article_id`)
- **Classes:** `PascalCase` (e.g., `HTMLScraper`, `VectorStore`)
- **Constants:** `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`, `DEFAULT_TIMEOUT`)
- **Files/Modules:** `snake_case` (e.g., `embedder.py`, `date_utils.py`)
- **Type Hinting:** Mandatory for all function signatures (e.g., `def clean_text(raw: str) -> str:`)

### Database (PostgreSQL)
- **Tables & Columns:** `snake_case` (e.g., `articles`, `published_date`)
- **Indexes:** Prefix with `idx_` (e.g., `idx_articles_date`)
- **Primary Keys:** UUIDs, defaulting to `gen_random_uuid()`

### Frontend & API
- **API Routes:** `kebab-case` and lowercase (e.g., `/api/v1/digest/today`)
- **HTML/CSS IDs & Classes:** `kebab-case` (e.g., `highlight-card`, `category-section`)
- **JS Variables:** `camelCase` (e.g., `fetchDigest`, `isDarkMode`)

---

## 2. Folder Structure

Always respect the defined modular architecture. Do not create new top-level directories without explicit approval.

```text
ai-news-pulse/
├── config/             # All YAML configuration files
├── src/                # All backend Python code
│   ├── scrapers/       # Data ingestion (HTML, RSS)
│   ├── processing/     # Cleaning, Deduplication, Chunking, Embedding
│   ├── rag/            # Retrieval, Summarization (Groq), Formatting
│   ├── storage/        # PostgreSQL and Pinecone wrappers
│   ├── delivery/       # FastAPI app and Email notifications
│   └── utils/          # Logging, Date handling, Config parsing
├── frontend/           # Static HTML, CSS, Vanilla JS
├── tests/              # Pytest unit and integration tests
└── data/               # Local persistence (raw HTML, generated JSON/MD)
```
*Note: Pipeline entry points (`scrape.py`, `embed.py`, `generate_digest.py`) live directly under `src/`.*

---

## 3. Libraries to Use

Do **not** introduce new libraries if an existing one can solve the problem.

- **Web Scraping:** `BeautifulSoup4`, `requests`, `feedparser`
- **Text Processing & Deduplication:** `langdetect`, `rapidfuzz`
- **Chunking:** `langchain.text_splitter` (`RecursiveCharacterTextSplitter`)
- **Embeddings:** `FlagEmbedding` (specifically BGE `BAAI/bge-small-en-v1.5`)
- **Vector Store:** `pinecone-client`
- **LLM Generation:** `groq` (Models: `llama-3.3-70b-versatile`, `llama-3.1-8b-instant`)
- **Database (Relational):** `psycopg2-binary` (or `asyncpg` if needed by FastAPI)
- **API Framework:** `fastapi`, `uvicorn`, `pydantic`
- **Data Validation & Config:** `pydantic`, `pyyaml`
- **Testing:** `pytest`

---

## 4. Error Handling Patterns

1. **Fail Gracefully at the Source:** If a single news source fails to scrape (HTTP 403, timeout, layout change), log an error, return 0 articles for that source, and **continue** to the next. Do not crash the entire ingestion pipeline.
2. **Exponential Backoff:** Use retries with exponential backoff for all external network calls (Groq API, Pinecone API, external scrapers) to handle transient 429s (Rate Limits) or 500/503s.
3. **Structured Logging:** Never use `print()`. Always use the `logging` module (configured in `src/utils/logger.py`). Include context in logs (e.g., `logger.error(f"Failed to scrape {source_name}: {str(e)}")`).
4. **LLM Fallbacks:** Always wrap the Groq API call in a `try-except`. If the primary 70B model fails or times out, immediately fall back to the 8B instant model.
5. **Idempotency:** Pipelines must be re-runnable. Catch and ignore "Unique Violation" errors in PostgreSQL gracefully, or use `INSERT ... ON CONFLICT DO NOTHING`.

---

## 5. Patterns to Avoid (Anti-Patterns)

1. **NO Hardcoded Credentials:** Never hardcode API keys, DB connection strings, or Webhook URLs. Always load them from environment variables via `os.environ.get()` or a `.env` file wrapper.
2. **NO Wildcard Imports:** Avoid `from module import *`. Be explicit about what you are importing.
3. **NO Blocking the Event Loop:** In FastAPI (`src/delivery/api.py`), do not use synchronous blocking calls (like synchronous `requests.get()` or heavy DB queries) inside an `async def` route. Use thread pools or `def` routes for synchronous code.
4. **NO Silent Failures:** Do not use `except Exception: pass`. If you catch a generic exception, you **must** log it.
5. **NO Direct DB Queries in Logic Modules:** Do not write raw SQL inside the scraping, embedding, or RAG modules. All database interactions must go through the dedicated CRUD wrappers in `src/storage/`.
6. **NO LLM Hallucinations:** Do not allow the LLM to output unsourced claims. Strictly enforce the prompt directive that every bullet point must have a markdown citation matching the injected context.