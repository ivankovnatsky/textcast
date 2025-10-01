import traceback
from pathlib import Path

import pytest
from click.testing import CliRunner

from textcast.chunks import TEXT_SEND_LIMIT, split_text
from textcast.cli import cli

from .conftest import ARTICLE_URL_HTML, ARTICLE_URL_JS


@pytest.mark.parametrize(
    "url, expected_exit_code",
    [
        (ARTICLE_URL_HTML, 0),
        (ARTICLE_URL_JS, 0),
    ],
)
def test_process_article_openai(url, expected_exit_code, capture_logging):
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
            "--speech-model",
            "tts-1",
            "--voice",
            "alloy",
            "--strip",
            "5",  # Strip the text by # of chars to reduce costs during testing
            "--yes",
            "--debug",
        ],
        catch_exceptions=False,  # Allow exceptions to propagate
    )

    print(f"\n--- Debug Output for URL: {url} ---")
    print(f"CLI Output:\n{result.output}")
    print(f"Exit Code: {result.exit_code}")

    print("Contents of /tmp directory:")
    print(list(Path("/tmp").glob("*")))

    try:
        output_audio_path = next(Path("/tmp").glob("*.mp3"))
        print(f"Found MP3 file: {output_audio_path}")
    except StopIteration:
        print("No MP3 file found in /tmp")
        raise

    print("--- End Debug Output ---")

    if result.exception:
        print("Exception occurred during CLI execution:")
        print(
            traceback.format_exception(
                type(result.exception), result.exception, result.exception.__traceback__
            )
        )

    assert result.exit_code == expected_exit_code
    assert output_audio_path.exists()

    # Check for debug logs
    log_output = capture_logging.getvalue()
    assert "Processing with OpenAI" in log_output
    assert "Text split into" in log_output, "Text splitting not logged"
    assert "Processing chunk" in log_output, "Chunk processing not logged"
    assert "Audio saved to" in log_output, "Audio save not logged"

    # Clean up
    output_audio_path.unlink()


def test_process_article_elevenlabs():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--url",
            ARTICLE_URL_HTML,
            "--directory",
            "/tmp",
            "--audio-format",
            "mp3",
            "--vendor",
            "elevenlabs",
            "--voice",
            "Sarah",  # Use a valid ElevenLabs voice
            "--strip",
            "5",  # Strip the text by # of chars to reduce costs during testing
            "--yes",
            "--debug",
        ],
    )
    assert result.exit_code == 0


def test_split_text():
    text = "This is a test text. " * 300  # Creating a long text to ensure it gets split
    chunks = split_text(text)

    # Ensure that the text is split into more than one chunk
    assert len(chunks) > 1

    # Ensure that each chunk is within the limit
    for chunk in chunks:
        assert len(chunk) <= TEXT_SEND_LIMIT
