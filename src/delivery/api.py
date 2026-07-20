from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
from datetime import date
import logging
import sys
from pathlib import Path

# Add project root to sys path to allow direct execution
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.utils.logger import setup_logger
from src.storage.digest_store import DigestStore
from src.utils.date_utils import get_current_utc_time, format_date_for_db

logger = setup_logger("api")

app = FastAPI(
    title="AI News Pulse API",
    description="REST API serving daily RAG digests for the AI News Pulse frontend.",
    version="1.0.0"
)

# Phase 5.6: CORS Middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, limit this to the frontend domain
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Global store connection
store = None

@app.on_event("startup")
async def startup_event():
    """Initializes the database connection pool on API startup."""
    global store
    try:
        store = DigestStore()
        logger.info("DigestStore initialized for API.")
    except Exception as e:
        logger.error(f"Failed to initialize database connection on startup: {e}")

def get_digest_by_date(target_date: str) -> Optional[Dict[str, Any]]:
    """Helper function to fetch a digest securely from PostgreSQL."""
    query = "SELECT date, highlight_json, markdown_content, metadata_json, generated_at FROM digests WHERE date = %s;"
    try:
        with store.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (target_date,))
                row = cur.fetchone()
                if row:
                    return dict(row)
    except Exception as e:
        logger.error(f"DB Error fetching digest for {target_date}: {e}")
    return None

def get_latest_digest() -> Optional[Dict[str, Any]]:
    """Helper function to fetch the absolute latest digest from PostgreSQL."""
    query = "SELECT date, highlight_json, markdown_content, metadata_json, generated_at FROM digests ORDER BY date DESC LIMIT 1;"
    try:
        with store.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                row = cur.fetchone()
                if row:
                    return dict(row)
    except Exception as e:
        logger.error(f"DB Error fetching latest digest: {e}")
    return None

# Phase 5.2: GET /v1/digest/today
@app.get("/v1/digest/today")
async def get_today_digest():
    """Returns the comprehensive AI digest for the current date."""
    today = format_date_for_db(get_current_utc_time())
    digest = get_digest_by_date(today)
    
    if not digest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Today's digest is not yet available. The pipeline may still be running."
        )
    return digest

@app.get("/v1/digest/latest")
async def get_latest():
    """Returns the most recent AI digest and indicates if it is from today."""
    today = format_date_for_db(get_current_utc_time())
    digest = get_latest_digest()
    
    if not digest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="No digests found."
        )
        
    digest["is_today"] = (str(digest["date"]) == today)
    return digest

# Phase 5.3: GET /v1/digest/{date}
@app.get("/v1/digest/{target_date}")
async def get_digest(target_date: date):
    """Returns the AI digest for a specific historical date (YYYY-MM-DD)."""
    digest = get_digest_by_date(target_date.isoformat())
    
    if not digest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"No digest found for date {target_date}."
        )
    return digest

# Phase 5.4: GET /v1/digest/archive
@app.get("/v1/digest/archive/list")
async def get_archive(limit: int = 30, offset: int = 0):
    """Returns a paginated list of available digests (used for the archive page)."""
    query = """
        SELECT date, highlight_json, metadata_json, generated_at 
        FROM digests 
        ORDER BY date DESC 
        LIMIT %s OFFSET %s;
    """
    try:
        with store.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (limit, offset))
                rows = cur.fetchall()
                return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"DB Error fetching archive: {e}")
        raise HTTPException(status_code=500, detail="Database error while fetching archive.")

# Phase 5.5: GET /v1/health
@app.get("/v1/health")
async def health_check():
    """Checks the health of the API and its connection to the database."""
    health_status = {"status": "ok", "database": "unknown"}
    
    try:
        with store.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
        health_status["database"] = "connected"
    except Exception:
        health_status["database"] = "disconnected"
        health_status["status"] = "degraded"
        
    return health_status

if __name__ == "__main__":
    import uvicorn
    # Allow running directly for local testing
    uvicorn.run("src.delivery.api:app", host="0.0.0.0", port=8000, reload=True)
