from bs4 import BeautifulSoup
from readability import Document
from playwright.sync_api import sync_playwright
import requests
from .common import RenderError


def is_js_required(soup):
    """Check if the content indicates JS is required"""
    # Check for elements that are often loaded by JavaScript
    js_indicators = [
        ("div", {"id": "app"}),
        ("div", {"id": "root"}),
        ("script", {}),
        ("noscript", {}),
    ]

    for tag_name, attr_dict in js_indicators:
        tag_elements = soup.find_all(tag_name, attr_dict)
        if tag_elements:
            return True

    return False


def fetch_content_with_requests(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(
            response.text, "html.parser"
        )  # <-- Create soup from response.text
        doc = Document(soup)  # <-- Pass the soup object to Document

        text = soup.get_text()
        title = doc.title()

        print(f"soup type is {type(soup)}")
        print(f"soup value is {soup}")
        if is_js_required(soup):
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
        print("Attempting to fetch and parse using requests.")
        return fetch_content_with_requests(url)
    except RenderError:
        print("Using Playwright to render the page.")
        return fetch_content_with_playwright(url)
