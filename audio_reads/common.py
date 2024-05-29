import click
import os
import random
import re
import string
from pathlib import Path

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


class RenderError(Exception):
    pass


def generate_lowercase_string():
    length = 10
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for _ in range(length))


def process_text_to_audio(
    text, title, vendor, directory, audio_format, model, voice, strip
):
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
