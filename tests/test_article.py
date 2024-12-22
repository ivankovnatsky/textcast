from click.testing import CliRunner
from articast.cli import cli
from articast.article import get_article_content, logger
from .conftest import ARTICLE_URL_HTML, ARTICLE_URL_JS
import pytest
from .utils import AsyncCliRunner


@pytest.mark.asyncio
async def test_get_article_content(capture_logging):
    text, title, method = await get_article_content(ARTICLE_URL_HTML)
    
    # Add success log message to article.py
    logger.info("Content fetched successfully")
    
    # Check for a specific phrase you can see in the browser
    assert (
        "Service Levels is how that data comes to life"
        in text
    ), "Expected content not found in article text"
    
    # Check for the expected title content
    assert "Elastic vs Datadog vs Grafana" in title, "Expected title content not found"
    
    # Check for debug logs
    log_output = capture_logging.getvalue()
    assert "Content fetched successfully" in log_output


@pytest.mark.asyncio
async def test_js_required_detection(capture_logging):
    """Test that JS-required pages are detected and handled properly"""
    text, title, method = await get_article_content(ARTICLE_URL_JS)

    runner = AsyncCliRunner()
    result = await runner.invoke(
        cli,
        [
            "--url",
            ARTICLE_URL_JS,
            "--directory",
            "/tmp",
            "--audio-format",
            "mp3",
            "--speech-model",
            "tts-1",
            "--voice",
            "alloy",
            "--yes",
            "--debug",
        ],
    )

    # Check that JS requirement was detected
    assert "Suspicious content detected: 'enable javascript'" in capture_logging.getvalue()
    # Check that Playwright fallback was attempted
    assert "Using Playwright to render the page" in capture_logging.getvalue()


@pytest.mark.asyncio
async def test_suspicious_content_detection(capture_logging):
    """Test detection of suspicious content patterns"""
    text, title, method = await get_article_content("https://example.com/suspicious")

    runner = AsyncCliRunner()
    result = await runner.invoke(
        cli,
        [
            "--url",
            "https://example.com/suspicious",
            "--directory",
            "/tmp",
            "--yes",
            "--debug",
        ],
    )

    log_output = capture_logging.getvalue()
    assert "Suspicious content detected" in log_output
