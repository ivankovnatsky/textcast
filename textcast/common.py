import logging
import os
import random
import re
import string
from pathlib import Path

import click

from .audiobookshelf import upload_to_audiobookshelf
from .elevenlabs import process_article_elevenlabs
from .openai import process_article_openai
from .podservice import upload_to_podservice

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
    except KeyError:
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
    except KeyError:
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


def process_text_to_audio(
    text,
    title,
    vendor,
    directory,
    audio_format,
    model,
    voice,
    strip,
    abs_url=None,
    abs_library=None,  # Library name or ID
    abs_folder_id=None,  # Optional folder ID (auto-detected if library is a name)
    # Deprecated parameters for backward compatibility
    abs_pod_lib_id=None,
    abs_pod_folder_id=None,
    # Podservice parameters
    podservice_url=None,
    source_url=None,  # Original article URL for GUID
    description=None,  # Episode description for podservice
    image_url=None,  # Episode artwork URL for podservice
):
    logger.info(f"Processing text to audio for title: {title}")
    logger.debug(
        f"Vendor: {vendor}, Format: {audio_format}, Model: {model}, Voice: {voice}"
    )
    logger.info(f"Text length: {len(text)} characters")
    logger.debug(
        f"Text content being sent for audio conversion:\n{'-' * 50}\n{text}\n{'-' * 50}"
    )

    if strip:
        logger.debug(f"Stripping text to {strip} characters")
        text = text[:strip]
        logger.debug(
            f"Text after stripping (length: {len(text)}):\n{'-' * 50}\n{text}\n{'-' * 50}"
        )

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

    # Handle backward compatibility with old parameter names
    if abs_pod_lib_id and not abs_library:
        abs_library = abs_pod_lib_id
        logger.debug("Using deprecated abs_pod_lib_id parameter")
    if abs_pod_folder_id and not abs_folder_id:
        abs_folder_id = abs_pod_folder_id
        logger.debug("Using deprecated abs_pod_folder_id parameter")

    # Track if any upload succeeded (for cleanup decision)
    upload_succeeded = False

    # Upload to Audiobookshelf if parameters are provided
    if abs_url and abs_library:
        logger.info("Uploading to Audiobookshelf...")
        success = upload_to_audiobookshelf(
            filename, abs_url, abs_library, abs_folder_id, title
        )
        if success:
            logger.info("Successfully uploaded to Audiobookshelf!")
            upload_succeeded = True
        else:
            logger.warning(
                "Failed to upload to Audiobookshelf, but audio file was created successfully"
            )
    else:
        logger.debug("Audiobookshelf parameters not provided, skipping upload")

    # Upload to Podservice if URL is provided
    if podservice_url:
        logger.info("Uploading to Podservice...")
        success = upload_to_podservice(
            file_path=filename,
            title=title,
            podservice_url=podservice_url,
            description=description,
            source_url=source_url,
            image_url=image_url,
        )
        if success:
            logger.info("Successfully uploaded to Podservice!")
            upload_succeeded = True
        else:
            logger.warning(
                "Failed to upload to Podservice, but audio file was created successfully"
            )
    else:
        logger.debug("Podservice URL not provided, skipping upload")

    # Clean up local audio file after successful upload to any target
    if upload_succeeded:
        try:
            os.remove(filename)
            logger.info(f"Deleted local audio file: {filename}")
        except Exception as e:
            logger.warning(f"Failed to delete local audio file {filename}: {str(e)}")
