import logging
import os
import random
import re
import string
from pathlib import Path
from typing import List, Optional, Union

import click

from .audiobookshelf import upload_to_audiobookshelf
from .elevenlabs import process_text_to_audio_elevenlabs
from .openai import process_text_to_audio_openai
from .podservice import upload_to_podservice
from .service_config import AudiobookshelfDestination, PodserviceDestination

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
        choices = ["eleven_multilingual_v2"]
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
        # ElevenLabs accepts voice IDs (e.g., "JBFqnCBsd6RMkjVDRZzb")
        # No strict validation - users can use any valid voice ID from their account
        return value
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


def upload_to_destinations(
    file_path: Path,
    title: str,
    destinations: Optional[
        List[Union[PodserviceDestination, AudiobookshelfDestination]]
    ] = None,
    source_url: Optional[str] = None,
    description: Optional[str] = None,
    image_url: Optional[str] = None,
    # Legacy parameters
    abs_url: Optional[str] = None,
    abs_library: Optional[str] = None,
    abs_folder_id: Optional[str] = None,
    podservice_url: Optional[str] = None,
) -> bool:
    """Upload audio file to configured destinations.

    Args:
        file_path: Path to audio file
        title: Title for the upload
        destinations: List of destination configs (new format)
        source_url: Original URL for GUID deduplication
        description: Episode description
        image_url: Episode artwork URL
        abs_url, abs_library, abs_folder_id: Legacy Audiobookshelf params
        podservice_url: Legacy Podservice URL

    Returns:
        True if any upload succeeded
    """
    upload_succeeded = False

    # Use new destinations list if provided
    if destinations:
        for dest in destinations:
            if not dest.enabled:
                logger.debug(f"Destination {dest.type} is disabled, skipping")
                continue

            if isinstance(dest, PodserviceDestination):
                if dest.url:
                    logger.info(f"Uploading to Podservice: {dest.url}")
                    success = upload_to_podservice(
                        file_path=file_path,
                        title=title,
                        podservice_url=dest.url,
                        description=description,
                        source_url=source_url,
                        image_url=image_url,
                    )
                    if success:
                        logger.info("Successfully uploaded to Podservice!")
                        upload_succeeded = True
                    else:
                        logger.warning("Failed to upload to Podservice")
                else:
                    logger.debug("Podservice destination has no URL, skipping")

            elif isinstance(dest, AudiobookshelfDestination):
                if dest.url:
                    library = dest.library_name or dest.library_id or None
                    logger.info(f"Uploading to Audiobookshelf: {dest.url}")
                    success = upload_to_audiobookshelf(
                        file_path,
                        dest.url,
                        library,
                        dest.folder_id or None,
                        title,
                    )
                    if success:
                        logger.info("Successfully uploaded to Audiobookshelf!")
                        upload_succeeded = True
                    else:
                        logger.warning("Failed to upload to Audiobookshelf")
                else:
                    logger.debug("Audiobookshelf destination has no URL, skipping")
    else:
        # Fall back to legacy parameters
        if abs_url and abs_library:
            logger.info("Uploading to Audiobookshelf...")
            success = upload_to_audiobookshelf(
                file_path, abs_url, abs_library, abs_folder_id, title
            )
            if success:
                logger.info("Successfully uploaded to Audiobookshelf!")
                upload_succeeded = True
            else:
                logger.warning("Failed to upload to Audiobookshelf")

        if podservice_url:
            logger.info("Uploading to Podservice...")
            success = upload_to_podservice(
                file_path=file_path,
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
                logger.warning("Failed to upload to Podservice")

    return upload_succeeded


def process_text_to_audio(
    text,
    title,
    vendor,
    directory,
    audio_format,
    model,
    voice,
    strip,
    # New destinations parameter
    destinations: Optional[
        List[Union[PodserviceDestination, AudiobookshelfDestination]]
    ] = None,
    # Legacy parameters (deprecated, use destinations instead)
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
        process_text_to_audio_openai(text, filename, model, voice)
    elif vendor == "elevenlabs":
        logger.info("Processing with ElevenLabs")
        process_text_to_audio_elevenlabs(text, filename, model, voice)

    logger.info(f"Audio processing complete for {title}")

    # Track if any upload succeeded (for cleanup decision)
    upload_succeeded = False

    # Use new destinations list if provided
    if destinations:
        for dest in destinations:
            if not dest.enabled:
                logger.debug(f"Destination {dest.type} is disabled, skipping")
                continue

            if isinstance(dest, PodserviceDestination):
                if dest.url:
                    logger.info(f"Uploading to Podservice: {dest.url}")
                    success = upload_to_podservice(
                        file_path=filename,
                        title=title,
                        podservice_url=dest.url,
                        description=description,
                        source_url=source_url,
                        image_url=image_url,
                    )
                    if success:
                        logger.info("Successfully uploaded to Podservice!")
                        upload_succeeded = True
                    else:
                        logger.warning(
                            "Failed to upload to Podservice, but audio file was created"
                        )
                else:
                    logger.debug("Podservice destination has no URL, skipping")

            elif isinstance(dest, AudiobookshelfDestination):
                if dest.server:
                    # Use library_name (preferred) or fall back to library_id
                    library = dest.library_name or dest.library_id or None
                    logger.info(f"Uploading to Audiobookshelf: {dest.server}")
                    success = upload_to_audiobookshelf(
                        filename,
                        dest.server,
                        library,
                        dest.folder_id or None,
                        title,
                    )
                    if success:
                        logger.info("Successfully uploaded to Audiobookshelf!")
                        upload_succeeded = True
                    else:
                        logger.warning(
                            "Failed to upload to Audiobookshelf, but audio file was created"
                        )
                else:
                    logger.debug("Audiobookshelf destination has no server, skipping")
    else:
        # Fall back to legacy parameters for backward compatibility
        # Handle backward compatibility with old parameter names
        if abs_pod_lib_id and not abs_library:
            abs_library = abs_pod_lib_id
            logger.debug("Using deprecated abs_pod_lib_id parameter")
        if abs_pod_folder_id and not abs_folder_id:
            abs_folder_id = abs_pod_folder_id
            logger.debug("Using deprecated abs_pod_folder_id parameter")

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
                    "Failed to upload to Audiobookshelf, but audio file was created"
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
                    "Failed to upload to Podservice, but audio file was created"
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
