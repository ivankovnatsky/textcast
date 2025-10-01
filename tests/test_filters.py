from unittest.mock import patch

from click.testing import CliRunner

from textcast.cli import cli
from textcast.filter_urls import filter_url

from .conftest import (
    ARTICLE_URL_HTML,
    ARTICLE_URL_JS,
    FILTERED_URL,
)


def test_filter_domains():
    """Test direct domain filtering"""
    assert not filter_url("https://youtube.com/watch?v=example123")
    assert not filter_url("https://youtu.be/example123")
    assert filter_url("https://medium.com/article")
    assert filter_url(ARTICLE_URL_HTML)
    assert filter_url(ARTICLE_URL_JS)


def test_redirect_handling(mock_requests, capture_logging):
    """Test handling of redirects to filtered domains"""
    redirect_url = "https://example.com/redirect"
    final_url = "https://youtube.com/watch?v=example123"

    # Mock HEAD requests for both URLs
    mock_requests.head(redirect_url, headers={"Location": final_url}, status_code=302)
    mock_requests.head(final_url, text="<html>YouTube content</html>", status_code=200)

    # Mock GET requests for both URLs (in case they're needed)
    mock_requests.get(redirect_url, headers={"Location": final_url}, status_code=302)
    mock_requests.get(final_url, text="<html>YouTube content</html>", status_code=200)

    runner = CliRunner()
    runner.invoke(
        cli,
        [
            "--url",
            redirect_url,
            "--directory",
            "/tmp",
            "--yes",
            "--debug",
        ],
    )

    log_output = capture_logging.getvalue()
    assert "Skipping URL that redirects to filtered domain" in log_output


@patch("textcast.filter_urls.get_final_url_with_browser")
def test_js_redirect_handling(mock_browser_redirect, capture_logging):
    """Test handling of JavaScript-based redirects"""
    mock_browser_redirect.return_value = (
        "https://youtube.com/watch?v=example123",
        True,
    )

    runner = CliRunner()
    runner.invoke(
        cli,
        [
            "--url",
            "https://newsletter.example.com/redirect/123",
            "--directory",
            "/tmp",
            "--yes",
            "--debug",
        ],
    )

    log_output = capture_logging.getvalue()
    assert "Skipping URL that redirects to filtered domain (Browser)" in log_output


def test_process_articles_with_filtered_urls(setup_article_file, capture_logging):
    """Test processing a mix of valid and filtered URLs"""
    # Create file with mixed URLs
    with open(setup_article_file, "w") as f:
        f.write(ARTICLE_URL_HTML + "\n")
        f.write(FILTERED_URL + "\n")
        f.write(ARTICLE_URL_JS + "\n")

    runner = CliRunner()
    runner.invoke(
        cli,
        [
            "--file-url-list",
            setup_article_file,
            "--directory",
            "/tmp",
            "--strip",
            "5",  # Strip the text by # of chars to reduce costs during testing
            "--yes",
            "--debug",
        ],
    )

    log_output = capture_logging.getvalue()
    assert "Skipping filtered domain" in log_output
    assert "Successfully processed" in log_output
    assert "Skipped: 1" in log_output
