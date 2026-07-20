import sys
from pathlib import Path
import os

# Add src to Python path so we can import from src.storage
sys.path.append(str(Path(__file__).resolve().parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from src.storage.article_store import ArticleStore
from src.storage.digest_store import DigestStore

def main():
    if not os.environ.get("DATABASE_URL"):
        print("Error: DATABASE_URL environment variable is not set.")
        print("Example: export DATABASE_URL='postgresql://ainewspulse:password123@localhost:5432/ainewspulse'")
        sys.exit(1)
        
    print("🚀 Initializing PostgreSQL Database Schema...")
    
    try:
        article_store = ArticleStore()
        article_store.init_schema()
        
        digest_store = DigestStore()
        digest_store.init_schema()
        
        print("✅ Database schema initialized successfully!")
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
