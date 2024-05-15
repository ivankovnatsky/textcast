from click.testing import CliRunner
from article_to_podcast.cli import cli
from article_to_podcast.main import TEXT_SEND_LIMIT, split_text
from article_to_podcast.article_fetcher import get_article_content
from pathlib import Path

ARTICLE_URL = "https://blog.kubetools.io/kopylot-an-ai-powered-kubernetes-assistant-for-devops-developers/"


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
            "1",  # Use 5% of the text to reduce costs during testing
        ],
        catch_exceptions=False,  # Allow exceptions to propagate
    )

    assert result.exit_code == 0
    output_audio_path = list(Path("/tmp").glob("*.mp3"))[
        0
    ]  # Find the generated audio file
    assert output_audio_path.exists()

    # Clean up
    # output_audio_path.unlink()
