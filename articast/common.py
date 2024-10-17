import click
import os
import random
import re
import string
import logging
from pathlib import Path
from .elevenlabs import process_article_elevenlabs
from .openai import process_article_openai

logger = logging.getLogger(__name__)


def format_filename(title, format):
    logger.debug(f"Formatting filename for title: {title}")
    formatted_title = re.sub(r"\W+", "-", title).strip("-").lower()
    result = f"{formatted_title}.{format}"
    logger.debug(f"Formatted filename: {result}")
    return result


def validate_models(ctx, param, value):
    logger.debug(f"Validating model: {value}")
    if value is None:
        return value
    try:
        vendor = ctx.params["vendor"]
    except:
        vendor = "openai"
    logger.debug(f"Vendor for model validation: {vendor}")
    if vendor == "elevenlabs":
        choices = ["eleven_monolingual_v1"]
    else:
        choices = ["tts-1", "tts-1-hd"]
    if value not in choices:
        logger.error(f"Invalid model choice: {value}")
        raise click.BadParameter(f"Invalid choice: {value}. Allowed choices: {choices}")
    return value


def validate_voice(ctx, param, value):
    logger.debug(f"Validating voice: {value}")
    if value is None:
        return value
    try:
        vendor = ctx.params["vendor"]
    except:
        vendor = "openai"
    logger.debug(f"Vendor for voice validation: {vendor}")
    if vendor == "elevenlabs":
        choices = ["Sarah"]
    else:
        choices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
    if value not in choices:
        logger.error(f"Invalid voice choice: {value}")
        raise click.BadParameter(f"Invalid choice: {value}. Allowed choices: {choices}")
    return value


class RenderError(Exception):
    pass


def generate_lowercase_string():
    length = 10
    letters = string.ascii_lowercase
    result = "".join(random.choice(letters) for _ in range(length))
    logger.debug(f"Generated lowercase string: {result}")
    return result


def process_text_to_audio(
    text, title, vendor, directory, audio_format, model, voice, strip
):
    logger.info(f"Processing text to audio for title: {title}")
    logger.debug(
        f"Vendor: {vendor}, Format: {audio_format}, Model: {model}, Voice: {voice}"
    )

    if strip:
        logger.debug(f"Stripping text to {strip} characters")
        text = text[:strip]

    os.makedirs(directory, exist_ok=True)
    logger.debug(f"Ensuring directory exists: {directory}")

    filename = Path(directory) / f"{format_filename(title, audio_format)}"
    logger.debug(f"Output filename: {filename}")

    if vendor == "openai":
        logger.info("Processing with OpenAI")
        process_article_openai(text, filename, model, voice)
    elif vendor == "elevenlabs":
        logger.info("Processing with ElevenLabs")
        process_article_elevenlabs(text, filename, model, voice)

    logger.info(f"Audio processing complete for {title}")
