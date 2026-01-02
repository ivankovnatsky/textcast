"""Scrape audio URLs from pages using Playwright (for JS-loaded players)."""

import logging
import re
from pathlib import Path
from typing import Optional

import requests
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

# Patterns to find audio URLs in rendered HTML
AUDIO_URL_PATTERNS = [
    r'https://[^"\'>\s]+\.mp3',
    r'https://[^"\'>\s]+\.m4a',
    r'https://[^"\'>\s]+\.ogg',
]


def scrape_audio_url(url: str) -> Optional[str]:
    """
    Render page with Playwright and grep for audio URLs.
    Returns first audio URL found, or None.
    """
    logger.info(f"Attempting Playwright scrape for audio URLs: {url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 720},
            )
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)  # Wait for iframes to load

            # Get full HTML including iframes
            html = page.content()
            for frame in page.frames:
                try:
                    html += frame.content()
                except Exception:
                    pass

            # Grep for audio URLs
            for pattern in AUDIO_URL_PATTERNS:
                matches = re.findall(pattern, html)
                if matches:
                    audio_url = matches[0]
                    logger.info(f"Found audio URL via Playwright: {audio_url}")
                    return audio_url

            logger.debug("No audio URLs found in page content")
            return None
        except Exception as e:
            logger.debug(f"Playwright scrape failed: {e}")
            return None
        finally:
            browser.close()


def download_audio_url(
    audio_url: str, output_dir: str, title: Optional[str] = None
) -> Optional[Path]:
    """Download audio file from URL using requests."""
    logger.info(f"Downloading audio from: {audio_url}")

    try:
        response = requests.get(audio_url, stream=True, timeout=60)
        response.raise_for_status()

        if title:
            # Sanitize title for filename
            safe_title = "".join(
                c for c in title if c.isalnum() or c in " -_"
            ).strip()[:100]
            filename = f"{safe_title}.mp3"
        else:
            filename = audio_url.split("/")[-1].split("?")[0]
            if not filename.endswith((".mp3", ".m4a", ".ogg")):
                filename += ".mp3"

        output_path = Path(output_dir) / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.info(f"Downloaded audio to: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Failed to download {audio_url}: {e}")
        return None


def try_scrape_and_download(url: str, output_dir: str) -> Optional[Path]:
    """
    Try to scrape audio URL from page and download it.
    Combined convenience function for the processor.

    Returns:
        Path to downloaded audio file, or None if not found/failed.
    """
    audio_url = scrape_audio_url(url)
    if not audio_url:
        return None

    return download_audio_url(audio_url, output_dir)
