from bs4 import BeautifulSoup
from readability import Document
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright
import requests
import logging
from .errors import ProcessingError, RenderError
from typing import Tuple
from .constants import DEFAULT_TIMEOUT, PREVIEW_LENGTH, SUSPICIOUS_TEXTS
import asyncio

logger = logging.getLogger(__name__)

def is_js_required(soup):
    """Check if the content indicates JS is required"""
    js_indicators = [
        ("div", {"id": "app"}),
        ("div", {"id": "root"}),
        ("script", {}),
        ("noscript", {}),
    ]

    # Add text-based checks
    js_required_texts = [
        "enable javascript and cookies to proceed",
        "enable javascript",
        "enable cookies",
        "javascript is required",
        "just a moment",
        "checking your browser",
    ]

    # Check for indicator elements
    for tag_name, attr_dict in js_indicators:
        tag_elements = soup.find_all(tag_name, attr_dict)
        if tag_elements:
            logger.debug(f"JS indicator found: {tag_name}")
            return True

    # Check for common JS requirement texts (case-insensitive)
    page_text = soup.get_text().lower().strip()
    for js_text in js_required_texts:
        if js_text.lower() in page_text:
            logger.debug(f"JS requirement text found: {js_text}")
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


async def fetch_content_with_playwright(url: str) -> Tuple[str, str]:
    """Fetch content using Playwright"""
    logger.debug(f"Starting fetch_content_with_playwright for URL: {url}")
    browser = None
    try:
        browser = await playwright.chromium.launch()
        logger.debug("Browser launched")
        
        context = await browser.new_context()
        logger.debug("New context created")
        
        page = await context.new_page()
        logger.debug("New page created")
        
        logger.debug(f"Navigating to URL: {url}")
        await page.goto(url)
        
        logger.debug("Waiting for body selector")
        await page.wait_for_selector('body')
        
        logger.debug("Getting page content")
        html_content = await page.content()
        logger.debug(f"Raw HTML content ({len(html_content)} chars):\n---\n{html_content[:PREVIEW_LENGTH]}...\n---")
        
        logger.debug("Parsing content with readability and BeautifulSoup")
        doc = Document(html_content)
        content = doc.summary()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Extract text and title
        text = soup.get_text().strip()
        title = doc.title()
        
        logger.debug(f"Extracted text ({len(text)} chars):\n---\n{text[:PREVIEW_LENGTH]}...\n---")
        logger.debug(f"Extracted title: {title}")
        
        await context.close()
        await browser.close()
        logger.debug("Browser closed")
        
        logger.info("Content fetched successfully using Playwright")
        return text, title
        
    except Exception as e:
        logger.error(f"Error while rendering page: {str(e)}")
        if browser:
            logger.debug("Closing browser")
            await browser.close()
            logger.debug("Browser closed")
        raise RenderError(f"Failed to render page: {str(e)}")


def fetch_content_with_playwright_sync(url: str) -> Tuple[str, str]:
    """Synchronous wrapper for fetch_content_with_playwright"""
    logger.debug(f"Starting fetch_content_with_playwright for URL: {url}")
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',  # Helps with memory issues
                    '--disable-gpu',  # Reduces issues in containerized environments
                ],
            )
            
            # Add common browser settings
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1280, 'height': 720},
                java_script_enabled=True,
                bypass_csp=True,  # Bypass Content Security Policy
                ignore_https_errors=True,  # Handle SSL issues
            )
            
            page = context.new_page()
            
            # Increase timeouts
            page.set_default_timeout(30000)  # 30 seconds
            page.set_default_navigation_timeout(30000)
            
            logger.debug(f"Navigating to URL: {url}")
            response = page.goto(
                url, 
                wait_until='networkidle', 
                timeout=30000
            )
            
            if not response:
                raise RenderError("Failed to get response from page")
            
            if response.status >= 400:
                raise RenderError(f"HTTP error {response.status}")
            
            logger.debug("Waiting for body selector")
            page.wait_for_selector('body', timeout=30000)
            
            # Wait for dynamic content and scrolling
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)  # 2 seconds
            
            logger.debug("Getting page content")
            html_content = page.content()
            logger.debug(f"Raw HTML content ({len(html_content)} chars):\n---\n{html_content[:PREVIEW_LENGTH]}...\n---")
            
            logger.debug("Parsing content with readability and BeautifulSoup")
            doc = Document(html_content)
            content = doc.summary()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract text and title
            text = soup.get_text(separator=' ', strip=True)
            title = doc.title()
            
            # Clean up
            page.close()
            context.close()
            browser.close()
            
            return text, title
            
        except Exception as e:
            logger.error(f"Error while rendering page: {str(e)}")
            raise RenderError(f"Failed to render with Playwright: {e}")
        
        finally:
            if 'browser' in locals():
                try:
                    browser.close()
                except Exception as e:
                    logger.warning(f"Failed to close browser: {e}")


def get_article_content(url: str) -> Tuple[str, str, str]:
    """Get article content from URL"""
    logger.info(f"Fetching content for URL: {url}")
    
    try:
        logger.debug("Attempting to fetch and parse using requests")
        text, title, js_required = fetch_content_with_requests(url)
        
        # Check for suspicious content patterns
        text_lower = text.lower()
        for suspicious in SUSPICIOUS_TEXTS:
            if suspicious in text_lower:
                logger.warning(f"Suspicious content detected: '{suspicious}'")
                raise ProcessingError(f"Suspicious content detected: '{suspicious}'. Article may not have loaded properly.")
        
        if js_required:
            logger.info("JavaScript may be required. Falling back to Playwright")
            raise ProcessingError("JavaScript may be required")
        
        logger.debug(f"Content extracted using requests ({len(text)} chars):\n---\n{text[:PREVIEW_LENGTH]}...\n---")
        logger.info("Content fetched successfully using requests")
        return text, title, "requests"
        
    except (RenderError, ProcessingError) as e:
        logger.warning(f"Request method failed: {e}. Using Playwright to render the page")
        text, title = fetch_content_with_playwright_sync(url)
        
        # Check for suspicious content patterns again after Playwright
        text_lower = text.lower()
        for suspicious in SUSPICIOUS_TEXTS:
            if suspicious in text_lower:
                logger.warning(f"Suspicious content detected: '{suspicious}'")
                raise ProcessingError(f"Suspicious content detected: '{suspicious}'. Article may not have loaded properly.")
        
        logger.debug(f"Content extracted using playwright ({len(text)} chars):\n---\n{text[:PREVIEW_LENGTH]}...\n---")
        logger.info("Content fetched successfully using Playwright")
        return text, title, "playwright"
