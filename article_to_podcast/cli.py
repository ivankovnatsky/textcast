import os
import click
from .main import process_article
from .article import get_article_content, is_js_required
from pathlib import Path
from .common import RenderError
import re


def format_filename(title, format):
    # Replace special characters with dashes and convert to lowercase
    formatted_title = re.sub(r"\W+", "-", title).strip("-").lower()
    return f"{formatted_title}.{format}"


@click.command()
@click.option("--url", type=str, help="URL of the article to be fetched.")
@click.option(
    "--file-url-list",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Path to a file with URLs placed on every new line.",
)
@click.option(
    "--directory",
    type=click.Path(exists=False, file_okay=False, writable=True),
    default=".",
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
    "--strip",
    type=click.IntRange(5, 2000),
    help="By what number of chars to strip the text to send to OpenAI.",
)
def cli(url, file_url_list, directory, audio_format, model, voice, strip):
    if not url and not file_url_list:
        raise click.UsageError("You must provide either --url or --file-url-list.")

    urls = []
    if url:
        urls.append(url)
    if file_url_list:
        with open(file_url_list, "r") as f:
            urls.extend([line.strip() for line in f if line.strip()])

    for url in urls:
        text, title = get_article_content(url)

        # Strip text by number of chars set
        if strip:
            text = text[:strip]

        # Create directory if it does not exist
        os.makedirs(directory, exist_ok=True)
        print(f"Processing article with `{title}` to audio..")
        filename = Path(directory) / f"{format_filename(title, audio_format)}"

        if is_js_required(text):
            raise RenderError(
                """
It seems like the page might not have rendered correctly, not 
sending text to OpenAI to avoid additinal costs.
"""
            )

        process_article(text, filename, model, voice)


if __name__ == "__main__":
    cli()
