import click
import os
import random
import re
import string
import logging
from pathlib import Path
from .elevenlabs import process_article_elevenlabs
from .openai import process_article_openai
import asyncio
from typing import Optional

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


def generate_lowercase_string():
    length = 10
    letters = string.ascii_lowercase
    result = "".join(random.choice(letters) for _ in range(length))
    logger.debug(f"Generated lowercase string: {result}")
    return result


def sanitize_filename(title: str) -> str:
    """Convert title to a safe filename"""
    # Remove or replace invalid characters
    safe_title = re.sub(r'[^\w\s-]', '', title)
    # Replace whitespace with hyphens
    safe_title = re.sub(r'[-\s]+', '-', safe_title).strip('-')
    # Convert to lowercase
    return safe_title.lower()


async def process_text_to_audio(
    text: str,
    title: str,
    directory: str,
    vendor: str = 'openai',
    model: Optional[str] = None,
    voice: Optional[str] = None,
    audio_format: str = 'mp3',
    strip: bool = False,
    **kwargs
) -> None:
    """Process text to audio file"""
    try:
        # Create output directory if it doesn't exist
        output_dir = Path(directory)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate safe filename from title
        safe_title = sanitize_filename(title)
        output_path = output_dir / f"{safe_title}.{audio_format}"

        # Skip if file already exists
        if output_path.exists():
            logger.warning(f"Output file already exists: {output_path}")
            return

        # Process based on vendor
        if vendor == 'elevenlabs':
            await process_article_elevenlabs(text, output_path, model, voice)
        else:
            await process_article_openai(text, output_path, model, voice)

        logger.info(f"Saved audio to: {output_path}")

    except Exception as e:
        logger.error(f"Failed to process audio: {str(e)}")
        raise
