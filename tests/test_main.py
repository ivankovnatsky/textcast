from click.testing import CliRunner
from article_to_podcast.cli import cli
from article_to_podcast.main import TEXT_SEND_LIMIT, split_text
from article_to_podcast.article_fetcher import get_article_content
from pathlib import Path
import pytest

ARTICLE_URL = "https://blog.kubetools.io/kopylot-an-ai-powered-kubernetes-assistant-for-devops-developers/"
ARTICLES_FILE_PATH = "/tmp/articles-file-list.txt"


@pytest.fixture
def setup_article_file():
    with open(ARTICLES_FILE_PATH, "w") as article_file_list:
        for _ in range(2):
            article_file_list.write(ARTICLE_URL + "\n")
    yield ARTICLES_FILE_PATH
    Path(ARTICLES_FILE_PATH).unlink()  # Clean up the file after the test


def test_split_text():
    text = "This is a test text. " * 300  # Creating a long text to ensure it gets split
    chunks = split_text(text)
    assert len(chunks) > 1  # Ensure that the text is split into more than one chunk
    for chunk in chunks:
        assert (
            len(chunk) <= TEXT_SEND_LIMIT
        )  # Ensure that each chunk is within the limit


def test_get_article_content():
    text, title = get_article_content(ARTICLE_URL)
    assert (
        "KoPylot\xa0is a cloud-native application performance monitoring (APM) solution that runs on Kubernetes"
        in text
    )
    assert "KoPylot" in title  # Checking a part of the title to ensure it's correct


def test_process_article():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--url",
            ARTICLE_URL,
            "--directory",
            "/tmp",
            "--audio-format",
            "mp3",
            "--model",
            "tts-1",
            "--voice",
            "alloy",
            "--shrink",
            "1",  # Use 1% of the text to reduce costs during testing
        ],
        catch_exceptions=False,  # Allow exceptions to propagate
    )

    assert result.exit_code == 0
    output_audio_path = list(Path("/tmp").glob("*.mp3"))[
        0
    ]  # Find the generated audio file
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
            "--shrink",
            "1",  # Use 1% of the text to reduce costs during testing
        ],
        catch_exceptions=False,  # Allow exceptions to propagate
    )

    assert result.exit_code == 0
    output_audio_paths = list(
        Path("/tmp").glob("*.mp3")
    )  # Find the generated audio files
    assert len(output_audio_paths) == 2  # Ensure two audio files are created

    for output_audio_path in output_audio_paths:
        assert output_audio_path.exists()
        # Clean up
        output_audio_path.unlink()
