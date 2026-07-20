import psycopg2
from psycopg2.extras import DictCursor
import os
import logging

logger = logging.getLogger(__name__)

class DigestStore:
    def __init__(self, connection_string: str = None):
        self.conn_str = connection_string or os.environ.get("DATABASE_URL")
        if not self.conn_str:
            raise ValueError("DATABASE_URL environment variable is not set")
            
    def get_connection(self):
        return psycopg2.connect(self.conn_str, cursor_factory=DictCursor)

    def init_schema(self):
        """Creates the digests table and its indexes if they do not exist."""
        schema = """
        CREATE TABLE IF NOT EXISTS digests (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            date DATE UNIQUE NOT NULL,
            highlight_json JSONB,
            sections_json JSONB,
            metadata_json JSONB,
            markdown_content TEXT,
            generated_at TIMESTAMPTZ DEFAULT NOW(),
            pipeline_status TEXT DEFAULT 'pending'
        );
        
        CREATE INDEX IF NOT EXISTS idx_digests_date ON digests(date);
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(schema)
                conn.commit()
            logger.info("Digests table schema initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize digests schema: {e}")
            raise

    def insert_digest(self, digest_data: dict):
        """Inserts or overwrites the daily generated RAG digest."""
        query = """
            INSERT INTO digests (date, highlight_json, markdown_content, pipeline_status)
            VALUES (%(date)s, %(highlight_json)s, %(markdown_content)s, 'completed')
            ON CONFLICT (date) DO UPDATE 
            SET highlight_json = EXCLUDED.highlight_json,
                markdown_content = EXCLUDED.markdown_content,
                pipeline_status = 'completed',
                generated_at = NOW();
        """
        import psycopg2.extras
        db_payload = {
            "date": digest_data["date"],
            "highlight_json": psycopg2.extras.Json({"executive_summary": digest_data["executive_summary"]}),
            "markdown_content": digest_data["full_markdown"]
        }
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, db_payload)
                conn.commit()
            logger.info(f"Successfully saved digest for {digest_data['date']} to PostgreSQL.")
        except Exception as e:
            logger.error(f"Failed to insert digest: {e}")
            raise
