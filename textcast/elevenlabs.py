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

    # Resolve voice name to ID if needed (voice IDs are 20 chars alphanumeric)
    voice_id = voice
    if not (len(voice) == 20 and voice.isalnum()):
        # Looks like a voice name, try to resolve it
        logger.debug(f"Looking up voice ID for name: {voice}")
        try:
            response = client.voices.search()
            for v in response.voices:
                if v.name.lower() == voice.lower():
                    voice_id = v.voice_id
                    logger.debug(f"Resolved voice name '{voice}' to ID '{voice_id}'")
                    break
            else:
                logger.warning(f"Voice '{voice}' not found, using as-is")
        except Exception as e:
            logger.warning(f"Failed to look up voice: {e}, using '{voice}' as-is")

    logger.debug(f"Generating audio with ElevenLabs (model={model}, voice_id={voice_id})")
    audio = client.text_to_speech.convert(
        voice_id=voice_id,
        text=text,
        model_id=model,
        output_format="mp3_44100_128",
    )

    logger.info(f"Saving audio to file: {filename}")
    save(audio, filename)
    logger.info("ElevenLabs processing completed successfully")
