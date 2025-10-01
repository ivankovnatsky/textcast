import logging
from typing import Optional, Tuple
from urllib.parse import urlparse

import requests
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

FILTERED_DOMAINS = {
    # Video platforms
    "youtube.com",
    "youtu.be",
    # Package repositories
    "pypi.org",
    "npmjs.com",
}


def get_final_url(url: str, max_redirects: int = 5) -> Optional[Tuple[str, bool]]:
    """
    Follow HTTP redirects and return the final URL.

    Args:
        url: Initial URL to check
        max_redirects: Maximum number of redirects to follow

    Returns:
        Tuple of (final_url, was_redirected) or None if failed
    """
    try:
        session = requests.Session()
        session.max_redirects = max_redirects
        response = session.head(url, allow_redirects=True, timeout=10)
        final_url = response.url
        was_redirected = len(response.history) > 0

        if was_redirected:
            logger.debug(f"URL redirected: {url} -> {final_url}")

        return final_url, was_redirected
    except Exception as e:
        logger.warning(f"Failed to check HTTP redirects for {url}: {str(e)}")
        return None


def get_final_url_with_browser(url: str) -> Optional[Tuple[str, bool]]:
    """Follow all redirects including JavaScript using a browser"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            initial_url = url
            response = page.goto(url, wait_until="networkidle")
            final_url = page.url
            was_redirected = initial_url != final_url
            return final_url, was_redirected
        except Exception as e:
            logger.warning(f"Failed to check browser redirects for {url}: {str(e)}")
            return None
        finally:
            browser.close()


def is_filtered_domain(url: str) -> bool:
    """Check if the domain is in the filtered list"""
    domain = urlparse(url).netloc.lower()
    return any(filtered in domain for filtered in FILTERED_DOMAINS)


def filter_url(url: str) -> bool:
    """Check URL with both HTTP and browser-based redirect detection"""
    if is_filtered_domain(url):
        logger.warning(f"Skipping filtered domain: {url}")
        return False

    # Try HTTP redirects first (faster)
    http_redirect = get_final_url(url)
    if http_redirect:
        final_url, was_redirected = http_redirect
        if was_redirected and is_filtered_domain(final_url):
            logger.warning(
                f"Skipping URL that redirects to filtered domain (HTTP): {url} -> {final_url}"
            )
            return False

    # If no HTTP redirect found, try browser-based check
    browser_redirect = get_final_url_with_browser(url)
    if browser_redirect:
        final_url, was_redirected = browser_redirect
        if was_redirected and is_filtered_domain(final_url):
            logger.warning(
                f"Skipping URL that redirects to filtered domain (Browser): {url} -> {final_url}"
            )
            return False

    return True
