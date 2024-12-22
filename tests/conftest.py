import pytest
import io
import logging
from pathlib import Path
import requests_mock

# Constants
ARTICLE_URL_HTML = "https://blog.alexewerlof.com/p/slo-elastic-datadog-grafana"
ARTICLE_URL_JS = "https://willgallego.com/2024/03/24/srecon24-americas-recap/"
ARTICLES_FILE_PATH = "/tmp/articles-file-list.txt"
GITHUB_REDIRECT_URL = "https://example.com/redirect"
FILTERED_URL = "https://github.com/user/repo"


@pytest.fixture
def capture_logging():
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    yield log_capture
    logger.removeHandler(handler)


@pytest.fixture
def mock_requests():
    with requests_mock.Mocker() as m:
        yield m


@pytest.fixture
def setup_article_file():
    with open(ARTICLES_FILE_PATH, "w") as article_file_list:
        article_file_list.write(ARTICLE_URL_HTML + "\n")
        article_file_list.write(ARTICLE_URL_JS + "\n")
    yield ARTICLES_FILE_PATH
    Path(ARTICLES_FILE_PATH).unlink()  # Clean up the file after the test
