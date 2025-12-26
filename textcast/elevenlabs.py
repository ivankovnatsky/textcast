import logging
import os
import sys

from elevenlabs import save
from elevenlabs.client import ElevenLabs

logger = logging.getLogger(__name__)

ELEVEN_TEXT_LIMIT_NONSIGNED = 500


def process_text_to_audio_elevenlabs(text, filename, model, voice):
    logger.info("Starting ElevenLabs processing")
    logger.debug(f"Text length: {len(text)}, Model: {model}, Voice: {voice}")

    try:
        api_key = os.environ["ELEVEN_API_KEY"]
        logger.debug("Using ElevenLabs API key from environment variable")
        client = ElevenLabs(api_key=api_key)
    except KeyError:
        logger.warning("ElevenLabs API key not found in environment variables")
        logger.info("Attempting to use ElevenLabs without API key")

        if len(text) > ELEVEN_TEXT_LIMIT_NONSIGNED:
            logger.error(
                f"Text length ({len(text)} chars) exceeds non-signed account limit of {ELEVEN_TEXT_LIMIT_NONSIGNED} chars"
            )
            print(
                f"""
This request's text has {len(text)} characters and exceeds the character limit
of {ELEVEN_TEXT_LIMIT_NONSIGNED} characters for non signed in accounts.
"""
            )
            sys.exit(0)
        else:
            logger.debug(
                "Text length within non-signed account limit, proceeding without API key"
            )
            client = ElevenLabs()

    logger.debug("Generating audio with ElevenLabs")
    audio = client.generate(text=text, voice=voice, model=model)

    logger.info(f"Saving audio to file: {filename}")
    save(audio, filename)
    logger.info("ElevenLabs processing completed successfully")
