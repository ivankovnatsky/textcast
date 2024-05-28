from pathlib import Path
import click
import os
import re

from .article import get_article_content
from .common import RenderError
from .elevenlabs import process_article_elevenlabs
from .openai import process_article_openai


def format_filename(title, format):
    # Replace special characters with dashes and convert to lowercase
    formatted_title = re.sub(r"\W+", "-", title).strip("-").lower()
    return f"{formatted_title}.{format}"


# Define models depending on the AI vendor
def validate_models(ctx, param, value):
    if value is None:
        return value

    try:
        vendor = ctx.params["vendor"]
    except:
        vendor = "openai"

    if vendor == "elevenlabs":
        choices = ["eleven_monolingual_v1"]
    else:
        choices = ["tts-1", "tts-1-hd"]

    if value not in choices:
        raise click.BadParameter(f"Invalid choice: {value}. Allowed choices: {choices}")
    return value


def validate_voice(ctx, param, value):
    if value is None:
        return value

    try:
        vendor = ctx.params["vendor"]
    except:
        vendor = "openai"

    if vendor == "elevenlabs":
        choices = ["Nicole"]
    else:
        choices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

    if value not in choices:
        raise click.BadParameter(f"Invalid choice: {value}. Allowed choices: {choices}")
    return value


@click.command()
@click.option("--url", type=str, help="URL of the article to be fetched.")
@click.option(
    "--vendor",
    type=click.Choice(["openai", "elevenlabs"]),
    default="openai",
    help="Choose vendor to use to convert text to audio.",
)
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
    "--model",
    callback=validate_models,
    default=None,
    help="The model to be used for text-to-speech conversion.",
)
@click.option(
    "--voice",
    callback=validate_voice,
    default=None,
    help="""
    OpenIA voices: alloy, echo, fable, onyx, nova, shimmer;
    ElevenLabs voices: Nicole.
    """,
)
@click.option(
    "--strip",
    type=click.IntRange(5, 2000),
    help="By what number of chars to strip the text to send to OpenAI.",
)
@click.option(
    "--audio-format",
    type=click.Choice(["mp3", "opus", "aac", "flac", "pcm"]),
    default="mp3",
    help="The audio format for the output file. Default is mp3.",
)
def cli(vendor, url, file_url_list, directory, audio_format, model, voice, strip):
    if not url and not file_url_list:
        raise click.UsageError("You must provide either --url or --file-url-list.")

    # Set model and voice based on the API vendor
    if vendor == "elevenlabs":
        model = model or "eleven_monolingual_v1"
        voice = voice or "Nicole"
    elif vendor == "openai":
        model = model or "tts-1"
        voice = voice or "alloy"

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

        if vendor == "openai":
            process_article_openai(text, filename, model, voice)
        elif vendor == "elevenlabs":
            process_article_elevenlabs(text, filename, model, voice)


if __name__ == "__main__":
    cli()
