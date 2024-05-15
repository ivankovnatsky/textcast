import click
from .main import process_article
from .article_fetcher import get_article_content
from pathlib import Path
import re


def format_filename(title, format):
    # Replace special characters with dashes and convert to lowercase
    formatted_title = re.sub(r"\W+", "-", title).strip("-").lower()
    return f"{formatted_title}.{format}"


@click.command()
@click.option(
    "--url", type=str, required=True, help="URL of the article to be fetched."
)
@click.option(
    "--directory",
    type=click.Path(exists=True, file_okay=False, writable=True),
    required=True,
    help="Directory where the output audio file will be saved. The filename will be derived from the article title.",
)
@click.option(
    "--audio-format",
    type=click.Choice(["mp3", "opus", "aac", "flac", "pcm"]),
    default="mp3",
    help="The audio format for the output file. Default is mp3.",
)
@click.option(
    "--model",
    type=click.Choice(["tts-1", "tts-1-hd"]),
    default="tts-1",
    help="The model to be used for text-to-speech conversion.",
)
@click.option(
    "--voice",
    type=click.Choice(["alloy", "echo", "fable", "onyx", "nova", "shimmer"]),
    default="alloy",
    help="""
    The voice to be used for the text-to-speech conversion. Voice options:
    alloy:   A balanced and neutral voice.
    echo:    A more dynamic and engaging voice.
    fable:   A narrative and storytelling voice.
    onyx:    A deep and resonant voice.
    nova:    A bright and energetic voice.
    shimmer: A soft and soothing voice.
    Experiment with different voices to find one that matches your desired tone and audience. The current voices are optimized for English.
    """,
)
@click.option(
    "--shrink",
    type=click.IntRange(0, 100),
    default=100,
    help="Percentage of the text to process. 0-100%. Default is 100%.",
)
def cli(url, directory, audio_format, model, voice, shrink):
    text, title = get_article_content(url)

    if shrink < 100:
        end_idx = len(text) * shrink // 100
        text = text[:end_idx]  # Limit the text based on the percentage
    filename = Path(directory) / f"{format_filename(title, audio_format)}"
    process_article(text, filename, model, voice)


if __name__ == "__main__":
    cli()
