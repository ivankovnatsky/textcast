import traceback
from pathlib import Path
from click.testing import CliRunner
from articast.cli import cli
from .conftest import ARTICLE_URL_HTML, ARTICLE_URL_JS, GITHUB_REDIRECT_URL, FILTERED_URL
import pytest
from articast.errors import ProcessingError
from .utils import AsyncCliRunner


@pytest.mark.asyncio
async def test_process_article_openai_file_list(setup_article_file, capture_logging):
    # Clean up existing MP3 files first
    for f in Path("/tmp").glob("*.mp3"):
        f.unlink()

    # Create test file with two valid URLs
    with open(setup_article_file, "w") as f:
        f.write(f"{ARTICLE_URL_HTML}\n{ARTICLE_URL_HTML}")

    runner = AsyncCliRunner()
    result = await runner.invoke(
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
@pytest.mark.asyncio
async def test_process_article_with_condense(capture_logging):
    runner = AsyncCliRunner()
    result = await runner.invoke(
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


def create_url_file(urls: list[str], tmp_path: Path) -> str:
    """Create a temporary file with URLs for testing"""
    url_file = tmp_path / "urls.txt"
    url_file.write_text("\n".join(urls))
    return str(url_file)


def test_process_articles_concurrent(mocker, tmp_path):
    # Mock dependencies
    mock_filter = mocker.patch('articast.processor.filter_url', return_value=True)
    mock_get_content = mocker.patch('articast.processor.get_article_content',
        return_value=('test content', 'Test Title', 'test_method'))
    mock_process_audio = mocker.patch('articast.common.process_text_to_audio', return_value=None)
    mock_process_articles = mocker.patch('articast.processor.process_articles_async')
    mock_process_articles.return_value = [
        {'url': ARTICLE_URL_HTML, 'success': True},
        {'url': ARTICLE_URL_JS, 'success': True},
        {'url': GITHUB_REDIRECT_URL, 'success': True}
    ]

    # Use real test URLs
    urls = [
        ARTICLE_URL_HTML,
        ARTICLE_URL_JS,
        GITHUB_REDIRECT_URL
    ]

    runner = CliRunner()
    result = runner.invoke(cli, [
        '--file-url-list', create_url_file(urls, tmp_path),
        '--directory', str(tmp_path),
        '--concurrency', '3',
        '--yes'
    ])

    assert result.exit_code == 0
    mock_process_articles.assert_called_once()


def test_process_articles_concurrent_with_failures(mocker, tmp_path):
    mock_process_articles = mocker.patch('articast.processor.process_articles_async')
    mock_process_articles.return_value = [
        {'url': ARTICLE_URL_HTML, 'success': True},
        {'url': ARTICLE_URL_JS, 'success': False, 'error': 'Failed to process'},
        {'url': GITHUB_REDIRECT_URL, 'success': True}
    ]

    urls = [
        ARTICLE_URL_HTML,
        ARTICLE_URL_JS,  # This one will fail
        GITHUB_REDIRECT_URL
    ]

    runner = CliRunner()
    result = runner.invoke(cli, [
        '--file-url-list', create_url_file(urls, tmp_path),
        '--directory', str(tmp_path),
        '--concurrency', '3',
        '--yes'
    ])

    assert result.exit_code == 0  # Should pass because some articles succeeded
    assert "Failed to process" in result.output
    assert "Successfully processed: 2" in result.output
    assert "Failed to process: 1" in result.output


def test_process_articles_concurrent_with_filter(mocker, tmp_path):
    mock_process_articles = mocker.patch('articast.processor.process_articles_async')
    mock_process_articles.return_value = [
        {'url': ARTICLE_URL_HTML, 'success': True},
        {'url': FILTERED_URL, 'success': False, 'skipped': True, 'error': 'URL filtered'},
        {'url': ARTICLE_URL_JS, 'success': True}
    ]

    urls = [
        ARTICLE_URL_HTML,
        FILTERED_URL,  # This one will be filtered
        ARTICLE_URL_JS
    ]

    runner = CliRunner()
    result = runner.invoke(cli, [
        '--file-url-list', create_url_file(urls, tmp_path),
        '--directory', str(tmp_path),
        '--concurrency', '3',
        '--yes'
    ])

    assert result.exit_code == 0  # Should pass because some articles succeeded
    assert "URL filtered" in result.output
    assert "Successfully processed: 2" in result.output
    assert "Skipped: 1" in result.output
