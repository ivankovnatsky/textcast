from click.testing import CliRunner
from articast.cli import cli
from articast.article import get_article_content
from .conftest import ARTICLE_URL_HTML


def test_get_article_content(capture_logging):
    text, title, method = get_article_content(ARTICLE_URL_HTML)

    # Check for a specific phrase you can see in the browser
    assert (
        "Service Levels is how that data comes to life and turn into actionable information"
        in text
    ), "Expected content not found in article text"

    # Check for the expected title content
    assert "Elastic vs Datadog vs Grafana" in title, "Expected title content not found"

    # Optionally check the method used
    assert method in ["requests", "playwright"], "Unexpected fetch method"

    # Check for debug logs
    log_output = capture_logging.getvalue()
    assert "Fetching content for URL:" in log_output
    assert "Content fetched successfully" in log_output


def test_js_required_detection(mock_requests, capture_logging):
    """Test that JS-required pages are detected and handled properly"""
    js_required_html = """
    <html>
        <body>
            <div>Please enable JavaScript to continue</div>
        </body>
    </html>
    """

    url = "https://example.com/js-required"
    mock_requests.get(url, text=js_required_html)

    runner = CliRunner()
    runner.invoke(
        cli,
        [
            "--url",
            url,
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


def test_suspicious_content_detection(mock_requests, capture_logging):
    """Test detection of suspicious content patterns"""
    suspicious_html = """
    <html>
        <body>
            <div>Just a moment... Checking your browser</div>
        </body>
    </html>
    """

    url = "https://example.com/suspicious"
    mock_requests.get(url, text=suspicious_html)

    runner = CliRunner()
    runner.invoke(
        cli,
        [
            "--url",
            url,
            "--directory",
            "/tmp",
            "--yes",
            "--debug",
        ],
    )

    log_output = capture_logging.getvalue()
    assert "Suspicious content detected" in log_output
