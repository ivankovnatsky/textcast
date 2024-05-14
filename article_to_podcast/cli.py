import click
from .main import process_article
from .article_fetcher import get_article_content
from pathlib import Path


@click.command()
@click.option("--url", type=str, help="URL of the article to be fetched.")
@click.option(
    "--filename",
    type=str,
    required=True,
    help="Path to the output audio file, including the filename and format.",
)
@click.option(
    "--model",
    type=str,
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
def cli(url, filename, model, voice):
    if url:
        text = get_article_content(url)
    else:
        raise click.UsageError("You must provide --url")

    process_article(text, filename, model, voice)


if __name__ == "__main__":
    cli()
