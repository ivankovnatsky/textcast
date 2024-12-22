import traceback
from pathlib import Path
from click.testing import CliRunner
from articast.cli import cli
from .conftest import ARTICLE_URL_HTML


def test_process_article_openai_file_list(setup_article_file, capture_logging):
    # Clean up existing MP3 files first
    for f in Path("/tmp").glob("*.mp3"):
        f.unlink()

    # Create test file with two valid URLs
    with open(setup_article_file, "w") as f:
        f.write(f"{ARTICLE_URL_HTML}\n{ARTICLE_URL_HTML}")

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

    # Check for debug logs
    log_output = capture_logging.getvalue()
    assert "Starting OpenAI processing" in log_output
    assert "Text split into" in log_output
    assert "Processing chunk" in log_output
    assert "Audio saved to" in log_output

    for output_audio_path in output_audio_paths:
        assert output_audio_path.exists()
        # Clean up
        output_audio_path.unlink()


# Add new test for condensing feature
def test_process_article_with_condense(capture_logging):
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
            "--speech-model",
            "tts-1",
            "--text-model",
            "gpt-4-turbo-preview",
            "--voice",
            "alloy",
            "--strip",
            "5",
            "--condense",
            "--condense-ratio",
            "0.5",
            "--yes",
            "--debug",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0

    # Check for debug logs related to condensing
    log_output = capture_logging.getvalue()
    assert "Starting OpenAI processing" in log_output
    assert "Condensing article..." in log_output
    assert "Using text_model: gpt-4-turbo-preview" in log_output
    assert "Text split into" in log_output
    assert "Processing chunk" in log_output
    assert "Audio saved to" in log_output

    # Clean up
    output_audio_path = next(Path("/tmp").glob("*.mp3"))
    assert output_audio_path.exists()
    output_audio_path.unlink()


def test_process_article_removes_successful_urls(setup_article_file, capture_logging):
    # Clean up existing MP3 files first
    for f in Path("/tmp").glob("*.mp3"):
        f.unlink()

    # Create test file with two valid URLs
    test_urls = [ARTICLE_URL_HTML, ARTICLE_URL_HTML + "?second"]
    with open(setup_article_file, "w") as f:
        f.write("\n".join(test_urls))

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
            "--speech-model",
            "tts-1",
            "--voice",
            "alloy",
            "--strip",
            "5",  # Strip the text by # of chars to reduce costs during testing
            "--yes",
            "--debug",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0

    # Verify that the URLs were removed from the file
    with open(setup_article_file, "r") as f:
        remaining_urls = [line.strip() for line in f if line.strip()]
    
    assert len(remaining_urls) == 0, f"Expected all URLs to be removed, but found: {remaining_urls}"

    # Check for debug logs
    log_output = capture_logging.getvalue()
    assert "Removed 2 successfully processed URLs" in log_output

    # Clean up generated audio files
    for f in Path("/tmp").glob("*.mp3"):
        f.unlink()
