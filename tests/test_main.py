from click.testing import CliRunner
from articast.cli import cli
from articast.chunks import TEXT_SEND_LIMIT, split_text
from articast.article import get_article_content
from pathlib import Path
import pytest

import sys
import traceback

ARTICLE_URL_HTML = "https://blog.kubetools.io/kopylot-an-ai-powered-kubernetes-assistant-for-devops-developers/"
ARTICLE_URL_JS = (
    "https://lab.scub.net/architecture-patterns-the-circuit-breaker-8f79280771f1"
)
ARTICLES_FILE_PATH = "/tmp/articles-file-list.txt"


@pytest.fixture
def setup_article_file():
    with open(ARTICLES_FILE_PATH, "w") as article_file_list:
        article_file_list.write(ARTICLE_URL_HTML + "\n")
        article_file_list.write(ARTICLE_URL_JS + "\n")
    yield ARTICLES_FILE_PATH
    # Path(ARTICLES_FILE_PATH).unlink()  # Clean up the file after the test


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
def test_process_article_openai(url, expected_exit_code):
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
            "5",
            "--yes",
        ],
        catch_exceptions=False,
    )

    print(f"\n--- Debug Output for URL: {url} ---")
    print(f"CLI Output:\n{result.output}")
    print(f"Exit Code: {result.exit_code}")

    print("Contents of /tmp directory:")
    print(list(Path("/tmp").glob("*")))

    if result.exception:
        print("Exception occurred during CLI execution:")
        print(
            traceback.format_exception(
                type(result.exception), result.exception, result.exception.__traceback__
            )
        )

    assert result.exit_code == expected_exit_code

    try:
        output_audio_path = next(Path("/tmp").glob("*.mp3"))
        print(f"Found MP3 file: {output_audio_path}")
    except StopIteration:
        print("No MP3 file found in /tmp")
        raise

    print("--- End Debug Output ---\n")

    # Clean up
    output_audio_path.unlink()


def test_process_article_elevenlabs():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--url",
            ARTICLE_URL_HTML,
            "--vendor",
            "elevenlabs",
            "--directory",
            "/tmp",
            "--strip",
            "5",  # Strip the text by # of chars to reduce costs during testing
            "--yes",
        ],
        catch_exceptions=False,  # Allow exceptions to propagate
    )

    assert result.exit_code == 0

    output_audio_path = next(
        Path("/tmp").glob("*.mp3")
    )  # Find the generated audio file
    assert output_audio_path.exists()

    # Clean up
    output_audio_path.unlink()


def test_process_article_openai_file_list(setup_article_file):
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
            "--yes",
        ],
        catch_exceptions=False,  # Allow exceptions to propagate
    )

    print(f"CLI Output:\n{result.output}")
    print(f"Exit Code: {result.exit_code}")

    print("Contents of /tmp directory:")
    print(list(Path("/tmp").glob("*")))

    if result.exception:
        print("Exception occurred during CLI execution:")
        print(
            traceback.format_exception(
                type(result.exception), result.exception, result.exception.__traceback__
            )
        )

    print("--- End Debug Output ---\n")

    assert result.exit_code == 0

    # Find the generated audio files
    output_audio_paths = list(Path("/tmp").glob("*.mp3"))
    assert len(output_audio_paths) == 2  # Ensure two audio files are created

    for output_audio_path in output_audio_paths:
        assert output_audio_path.exists()
        # Clean up
        output_audio_path.unlink()
