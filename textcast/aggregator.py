import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .errors import ProcessingError

logger = logging.getLogger(__name__)

# Aggregator site configurations
# Each site can have specific rules for extracting article links
AGGREGATOR_CONFIGS: Dict[str, Dict[str, Any]] = {
    "sreweekly.com": {
        "name": "SRE Weekly",
        "link_selector": 'a[target="_blank"]',  # Only links with target="_blank"
        "exclude_patterns": [
            r"wp-content",  # WordPress assets
            r"sreweekly\.com",  # Internal links
        ],
    },
}

# Known aggregator URL patterns for auto-detection
AGGREGATOR_PATTERNS = [
    r"sreweekly\.com",
]


def get_aggregator_config(url: str) -> Optional[Dict[str, Any]]:
    """
    Get the configuration for a specific aggregator site.

    Args:
        url: URL to get configuration for

    Returns:
        Dict: Configuration dict for the site, or None if no specific config
    """
    url_lower = url.lower()

    # Check each configured aggregator site
    for domain, config in AGGREGATOR_CONFIGS.items():
        if domain in url_lower:
            logger.debug(f"URL matches aggregator config: {config['name']}")
            return config

    return None


def is_aggregator_url(url: str) -> bool:
    """
    Detect if a URL is likely an aggregator page containing multiple article links.

    Args:
        url: URL to check

    Returns:
        bool: True if URL appears to be an aggregator
    """
    url_lower = url.lower()

    # Check for known aggregator patterns in URL
    for pattern in AGGREGATOR_PATTERNS:
        if re.search(pattern, url_lower):
            logger.debug(f"URL matches aggregator pattern: {pattern}")
            return True

    return False


def extract_article_urls(url: str, html_content: str) -> List[str]:
    """
    Extract article URLs from an aggregator page.

    Args:
        url: The aggregator page URL (for resolving relative links)
        html_content: HTML content of the aggregator page

    Returns:
        List[str]: List of extracted article URLs
    """
    soup = BeautifulSoup(html_content, "html.parser")
    article_urls = []
    seen_urls = set()

    # Get site-specific configuration if available
    config = get_aggregator_config(url)

    # Default selector if no specific config
    link_selector = 'a[target="_blank"]'  # Default: external links
    exclude_patterns = []

    if config:
        link_selector = config.get("link_selector", link_selector)
        exclude_patterns = config.get("exclude_patterns", [])
        logger.debug(f"Using config for {config['name']}")
    else:
        logger.debug("Using default link extraction")

    # Find links based on selector
    links_to_process = soup.select(link_selector)
    logger.debug(f"Found {len(links_to_process)} links with selector '{link_selector}'")

    for link in links_to_process:
        href = link.get("href", "")
        if not href:
            continue

        # Skip anchors, mailto, and javascript links
        if (
            href.startswith("#")
            or href.startswith("mailto:")
            or href.startswith("javascript:")
        ):
            continue

        # Convert relative URLs to absolute
        absolute_url = urljoin(url, href)
        parsed = urlparse(absolute_url)

        # Skip non-HTTP(S) URLs
        if parsed.scheme not in ["http", "https"]:
            continue

        # Apply site-specific exclusion patterns
        if any(
            re.search(pattern, absolute_url.lower()) for pattern in exclude_patterns
        ):
            continue

        # Check if we've seen this URL already
        if absolute_url not in seen_urls:
            seen_urls.add(absolute_url)
            article_urls.append(absolute_url)
            logger.debug(f"Found article URL: {absolute_url}")

    logger.info(f"Extracted {len(article_urls)} unique article URLs from aggregator")
    return article_urls


def process_aggregator_url(url: str) -> List[str]:
    """
    Process an aggregator URL and extract all article links.

    Args:
        url: The aggregator URL to process

    Returns:
        List[str]: List of article URLs extracted from the aggregator

    Raises:
        ProcessingError: If unable to fetch or parse the aggregator page
    """
    logger.info(f"Processing aggregator URL: {url}")

    try:
        # First try with requests
        logger.debug("Fetching aggregator page with requests")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        html_content = response.text

    except requests.RequestException as e:
        logger.warning(f"Failed to fetch with requests: {e}. Trying with Playwright")
        try:
            # Fallback to Playwright for JS-heavy pages
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="networkidle", timeout=30000)
                html_content = page.content()
                browser.close()
        except Exception as e:
            raise ProcessingError(f"Failed to fetch aggregator page: {e}")

    # Extract article URLs
    article_urls = extract_article_urls(url, html_content)

    if not article_urls:
        logger.warning("No article URLs found in aggregator page")
        raise ProcessingError("No article URLs found in aggregator page")

    return article_urls


def detect_and_expand_aggregator(url: str) -> Tuple[bool, Optional[List[str]]]:
    """
    Check if URL is an aggregator and if so, extract article URLs.

    Args:
        url: URL to check and potentially expand

    Returns:
        Tuple[bool, Optional[List[str]]]: (is_aggregator, article_urls)
    """
    # Check if it's likely an aggregator
    if not is_aggregator_url(url):
        return False, None

    logger.info(f"Detected aggregator URL: {url}")

    try:
        article_urls = process_aggregator_url(url)
        return True, article_urls
    except ProcessingError as e:
        logger.error(f"Failed to process aggregator: {e}")
        # Even if we detected it as aggregator but failed to parse,
        # we return that it was detected as one
        return True, None
