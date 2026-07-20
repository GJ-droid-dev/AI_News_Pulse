import sys
import logging
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from src.utils.config_loader import ConfigLoader
from src.utils.logger import setup_logger
from src.utils.date_utils import parse_date, format_date_for_db
from src.scrapers.html_scraper import HTMLScraper
from src.scrapers.rss_scraper import RSSScraper
from src.processing.cleaner import ArticleCleaner
from src.processing.deduplicator import Deduplicator
from src.storage.article_store import ArticleStore

logger = setup_logger("scrape_pipeline")

def main():
    logger.info("🚀 Starting AI News Pulse Ingestion Pipeline...")
    
    # 1. Load Configs
    try:
        settings = ConfigLoader.load_settings()
        sources_config = ConfigLoader.load_sources()
    except Exception as e:
        logger.error(f"Failed to load configurations: {e}")
        sys.exit(1)

    max_articles = settings.get("pipeline", {}).get("max_articles_per_source", 20)
    
    # 2. Initialize Components
    try:
        store = ArticleStore()
        cleaner = ArticleCleaner(min_length=300)
        dedup = Deduplicator(article_store=store, threshold=85.0)
    except Exception as e:
        logger.error(f"Failed to initialize pipeline components. Is PostgreSQL running? Error: {e}")
        sys.exit(1)

    total_scraped = 0
    total_inserted = 0
    sources = sources_config.get("sources", [])

    # 3. Process Each Source
    for source in sources:
        source_name = source.get("name")
        source_type = source.get("type")
        
        logger.info(f"Processing source: {source_name} ({source_type})")
        
        if source_type == "rss":
            scraper = RSSScraper(source)
        elif source_type == "html":
            scraper = HTMLScraper(source)
        else:
            logger.warning(f"Unknown source type '{source_type}' for {source_name}. Skipping.")
            continue
            
        try:
            raw_articles = scraper.scrape()
        except Exception as e:
            logger.error(f"Failed to scrape {source_name}: {e}")
            continue

        inserted_for_source = 0
        for raw in raw_articles:
            if inserted_for_source >= max_articles:
                logger.info(f"Reached max limit ({max_articles}) for {source_name}. Skipping remainder.")
                break
                
            total_scraped += 1
            
            # Step A: Clean & Filter
            cleaned = cleaner.process_article(raw)
            if not cleaned:
                continue
                
            # Step B: Deduplicate
            if dedup.is_duplicate(cleaned):
                continue
                
            # Step C: Parse Date
            dt = parse_date(cleaned.get("published_date"))
            cleaned["published_date"] = format_date_for_db(dt)
            
            # Step D: Store in PostgreSQL
            try:
                store.insert_article(cleaned)
                inserted_for_source += 1
                total_inserted += 1
            except Exception as e:
                logger.error(f"Error inserting article from {source_name}: {e}")

        logger.info(f"Finished {source_name}. Inserted {inserted_for_source} new articles.")

    logger.info(f"✅ Ingestion Pipeline Complete! Scraped: {total_scraped} | Inserted: {total_inserted}")

if __name__ == "__main__":
    main()
