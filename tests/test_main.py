from click.testing import CliRunner
from article_to_podcast.cli import cli
from article_to_podcast.chunks import TEXT_SEND_LIMIT, split_text
from article_to_podcast.article import get_article_content
from pathlib import Path
import pytest

ARTICLE_URL_HTML = "https://blog.kubetools.io/kopylot-an-ai-powered-kubernetes-assistant-for-devops-developers/"
ARTICLE_URL_JS = (
    "https://lab.scub.net/architecture-patterns-the-circuit-breaker-8f79280771f1"
)
ARTICLES_FILE_PATH = "/tmp/articles-file-list.txt"


@pytest.fixture
def setup_article_file():
    with open(ARTICLES_FILE_PATH, "w") as article_file_list:
        for _ in range(2):
            article_file_list.write(ARTICLE_URL_HTML + "\n")
    yield ARTICLES_FILE_PATH
    Path(ARTICLES_FILE_PATH).unlink()  # Clean up the file after the test


def test_split_text():
    text = "This is a test text. " * 300  # Creating a long text to ensure it gets split
    chunks = split_text(text)

    # Ensure that the text is split into more than one chunk
    assert len(chunks) > 1

    # Ensure that each chunk is within the limit
    for chunk in chunks:
        assert len(chunk) <= TEXT_SEND_LIMIT


def test_get_article_content():
    text, title = get_article_content(ARTICLE_URL_HTML)

    # Check if a known phrase is in the text and title
    assert (
        "KoPylot\xa0is a cloud-native application performance monitoring (APM) solution that runs on Kubernetes"
        in text
    )
    assert "KoPylot" in title  # Checking a part of the title to ensure it's correct


@pytest.mark.parametrize(
    "url, expected_exit_code",
    [
        (ARTICLE_URL_HTML, 0),
        (ARTICLE_URL_JS, 0),
    ],
)
def test_process_article(url, expected_exit_code):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--url",
            url,
            "--directory",
            "/tmp",
            "--audio-format",
            "mp3",
            "--model",
            "tts-1",
            "--voice",
            "alloy",
            "--strip",
            "5",  # Strip the text by # of chars to reduce costs during testing
        ],
        catch_exceptions=False,  # Allow exceptions to propagate
    )

    assert result.exit_code == expected_exit_code

    output_audio_path = next(
        Path("/tmp").glob("*.mp3")
    )  # Find the generated audio file
    assert output_audio_path.exists()

    # Clean up
    output_audio_path.unlink()


def test_process_article_file_list(setup_article_file):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--file-url-list",
            setup_article_file,
            "--directory",
            "/tmp",
            "--audio-format",
            "mp3",
            "--model",
            "tts-1",
            "--voice",
            "alloy",
            "--strip",
            "5",  # Strip the text by # of chars to reduce costs during testing
        ],
        catch_exceptions=False,  # Allow exceptions to propagate
    )

    assert result.exit_code == 0

    # Find the generated audio files
    output_audio_paths = list(Path("/tmp").glob("*.mp3"))
    assert len(output_audio_paths) == 2  # Ensure two audio files are created

    for output_audio_path in output_audio_paths:
        assert output_audio_path.exists()
        # Clean up
        output_audio_path.unlink()
