import psycopg2
from psycopg2.extras import DictCursor
import os
import logging

logger = logging.getLogger(__name__)

class ArticleStore:
    def __init__(self, connection_string: str = None):
        self.conn_str = connection_string or os.environ.get("DATABASE_URL")
        if not self.conn_str:
            raise ValueError("DATABASE_URL environment variable is not set")
            
    def get_connection(self):
        return psycopg2.connect(self.conn_str, cursor_factory=DictCursor)

    def init_schema(self):
        """Creates the articles table and its indexes if they do not exist."""
        schema = """
        CREATE TABLE IF NOT EXISTS articles (
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
        
        CREATE INDEX IF NOT EXISTS idx_articles_date ON articles(published_date);
        CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source_name);
        CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category);
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(schema)
                conn.commit()
            logger.info("Articles table schema initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize articles schema: {e}")
            raise

    def insert_article(self, article: dict):
        """Inserts a cleaned, deduplicated article into the database."""
        query = """
            INSERT INTO articles (title, url, source_name, category, body_text, body_hash, published_date, language)
            VALUES (%(title)s, %(url)s, %(source_name)s, %(category)s, %(body_text)s, %(body_hash)s, %(published_date)s, %(language)s)
            ON CONFLICT (url) DO NOTHING
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, article)
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to insert article {article.get('url')}: {e}")
            raise

    def get_articles_by_date(self, target_date: str) -> list:
        """Fetches all articles published or scraped on the given date (YYYY-MM-DD)."""
        query = """
            SELECT id, title, url, source_name, category, body_text, published_date, language 
            FROM articles 
            WHERE published_date = %s
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (target_date,))
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Failed to fetch articles for date {target_date}: {e}")
            return []

    def get_article_counts_by_category(self, target_date: str) -> dict:
        """Returns the number of articles per category for a given date."""
        query = """
            SELECT category, COUNT(*) as count
            FROM articles 
            WHERE published_date = %s
            GROUP BY category
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (target_date,))
                    rows = cur.fetchall()
                    return {row['category']: row['count'] for row in rows}
        except Exception as e:
            logger.error(f"Failed to fetch article counts for date {target_date}: {e}")
            return {}
