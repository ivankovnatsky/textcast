from bs4 import BeautifulSoup
from readability import Document
from playwright.sync_api import sync_playwright
import requests
from .common import RenderError


def is_js_required(content):
    """Check if the content indicates JS is required"""
    phrases = [
        "Enable JavaScript to run this app.",
        "Please enable JavaScript to view the page content.",
        "Enable JavaScript and cookies to continue",
    ]
    return any(phrase.lower() in content.lower() for phrase in phrases)


def fetch_content_with_requests(url):
    try:
        response = requests.get(url, timeout=10)  # Adjust timeout as needed
        response.raise_for_status()

        doc = Document(response.text)
        soup = BeautifulSoup(doc.summary(), "html.parser")
        text = soup.get_text()
        title = doc.title()

        if is_js_required(text):
            raise RenderError("JavaScript is required to load this page.")

        return text, title
    except requests.RequestException as e:
        raise RenderError(f"Request failed: {e}")
    except Exception as e:
        raise RenderError(f"Parsing failed: {e}")


def fetch_content_with_playwright(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate to the URL
        page.goto(url)

        # Wait for the page to load completely
        page.wait_for_load_state("networkidle")

        # Get the rendered HTML
        html = page.content()

        # Use BeautifulSoup and readability to extract text and title
        doc = Document(html)
        soup = BeautifulSoup(doc.summary(), "html.parser")
        title = doc.title()
        text = soup.get_text()

        browser.close()

        return text, title


def get_article_content(url):
    try:
        # Attempt to fetch and parse using requests
        return fetch_content_with_requests(url)
    except RenderError:
        # Fallback to Playwright if requests fail
        return fetch_content_with_playwright(url)
