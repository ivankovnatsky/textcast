from bs4 import BeautifulSoup
from readability import Document
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import requests
import logging
from .common import RenderError

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10000  # 10 seconds (in milliseconds)

def is_js_required(soup):
    """Check if the content indicates JS is required"""
    js_indicators = [
        ("div", {"id": "app"}),
        ("div", {"id": "root"}),
        ("script", {}),
        ("noscript", {}),
    ]

    for tag_name, attr_dict in js_indicators:
        tag_elements = soup.find_all(tag_name, attr_dict)
        if tag_elements:
            logger.debug(f"JS indicator found: {tag_name}")
            return True

    logger.debug("No JS indicators found")
    return False


def fetch_content_with_requests(url):
    logger.debug(f"Fetching content with requests from URL: {url}")
    try:
        response = requests.get(url, timeout=DEFAULT_TIMEOUT/1000)  # Convert ms to seconds
        response.raise_for_status()
        html = response.text
        soup = BeautifulSoup(html, "html.parser")
        doc = Document(html)
        text = doc.summary()
        title = doc.title()

        js_required = is_js_required(soup)
        logger.debug(f"JS required: {js_required}")

        return text, title, js_required
    except requests.RequestException as e:
        logger.error(f"Request failed: {e}")
        raise RenderError(f"Request failed: {e}")
    except Exception as e:
        logger.error(f"Parsing failed: {e}")
        raise RenderError(f"Parsing failed: {e}")


def fetch_content_with_playwright(url, timeout=DEFAULT_TIMEOUT):
    logger.debug(f"Starting fetch_content_with_playwright for URL: {url}")
    with sync_playwright() as p:
        browser = None
        try:
            browser = p.chromium.launch(headless=True)
            logger.debug("Browser launched")
            context = browser.new_context()
            logger.debug("New context created")
            page = context.new_page()
            logger.debug("New page created")

            logger.debug(f"Navigating to URL: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            logger.debug("Navigation completed")

            logger.debug("Waiting for body selector")
            page.wait_for_selector("body", timeout=timeout)
            logger.debug("Body selector found")

            logger.debug("Getting page content")
            html = page.content()
            logger.debug("Page content retrieved")

            logger.debug("Parsing content with readability and BeautifulSoup")
            doc = Document(html)
            soup = BeautifulSoup(doc.summary(), "html.parser")
            title = doc.title()
            text = soup.get_text()
            logger.debug("Content parsed successfully")

            return text, title
        except Exception as e:
            logger.error(f"Error while rendering page: {str(e)}")
            raise RenderError(f"Failed to render page: {str(e)}")
        finally:
            if browser:
                logger.debug("Closing browser")
                browser.close()
                logger.debug("Browser closed")


def get_article_content(url):
    logger.info(f"Fetching content for URL: {url}")
    try:
        logger.debug("Attempting to fetch and parse using requests")
        text, title, js_required = fetch_content_with_requests(url)
        if js_required:
            logger.info("JavaScript may be required. Falling back to Playwright")
            raise RenderError("JavaScript may be required")
        logger.info("Content fetched successfully using requests")
        return text, title
    except RenderError as e:
        logger.warning(f"Request method failed: {e}. Using Playwright to render the page")
        try:
            text, title = fetch_content_with_playwright(url)
            logger.info("Content fetched successfully using Playwright")
            return text, title
        except RenderError as e:
            logger.error(f"Playwright method failed: {e}")
            raise
