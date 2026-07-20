from datetime import datetime, timezone
import dateutil.parser
import logging

logger = logging.getLogger(__name__)

def get_current_utc_time() -> datetime:
    """Returns the current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)

def parse_date(date_string: str) -> datetime:
    """
    Parses a string into a timezone-aware UTC datetime object.
    If parsing fails, it logs a warning and returns the current UTC time.
    """
    if not date_string:
        return get_current_utc_time()
        
    try:
        parsed = dateutil.parser.parse(date_string)
        
        # Ensure it is timezone aware and cast to UTC
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        else:
            parsed = parsed.astimezone(timezone.utc)
            
        return parsed
    except Exception as e:
        logger.warning(f"Failed to parse date string '{date_string}': {e}. Falling back to current time.")
        return get_current_utc_time()

def format_date_for_db(dt: datetime) -> str:
    """Formats datetime for PostgreSQL DATE storage (YYYY-MM-DD)."""
    return dt.strftime("%Y-%m-%d")
