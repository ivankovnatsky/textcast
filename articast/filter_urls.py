import logging

logger = logging.getLogger(__name__)

def filter_url(url: str) -> bool:
    """
    Check if the URL should be processed.
    Early filtering of known non-text content URLs (like video platforms) 
    before attempting more complex content extraction.
    
    Args:
        url: URL to check
    
    Returns:
        bool: True if URL should be processed, False if it should be skipped
    """
    filtered_domains = [
        "youtube.com",  # Video content
        "youtu.be",    # YouTube short URLs
    ]
    
    for domain in filtered_domains:
        if domain in url:
            logger.warning(f"Skipping unsupported URL ({domain}): {url}")
            return False
    
    return True
