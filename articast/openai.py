import io
import time
import logging
from pathlib import Path
from openai import OpenAI
from pydub import AudioSegment
from .chunks import split_text
from .filename import generate_unique_filename

logger = logging.getLogger(__name__)

SILENCE_TIME_MS = 3000


def process_article_openai(text, filename, model, voice):
    logger.info(f"Starting OpenAI processing for file: {filename}")
    logger.debug(f"Model: {model}, Voice: {voice}")

    client = OpenAI()
    chunks = split_text(text)
    logger.info(f"Text split into {len(chunks)} chunks")

    output_path = Path(filename)
    output_format = output_path.suffix.lstrip(".")

    if output_path.exists():
        logger.debug(f"File {output_path} already exists, generating unique filename")
        output_path = generate_unique_filename(output_path)
        logger.info(f"New unique filename: {output_path}")

    combined_audio = AudioSegment.empty()
    success = True

    for i, chunk in enumerate(chunks, start=1):
        logger.info(f"Processing chunk {i}/{len(chunks)} ({len(chunk)} characters)")
        try:
            start_time = time.time()
            response = client.audio.speech.create(model=model, voice=voice, input=chunk)
            processing_time = time.time() - start_time
            logger.info(
                f"Chunk {i}/{len(chunks)} processed in {processing_time:.2f} seconds"
            )

            part_audio = AudioSegment.from_file(
                io.BytesIO(response.content), format=output_format
            )
            logger.debug(f"Audio segment created for chunk {i}/{len(chunks)}")

            combined_audio += part_audio
            logger.debug(f"Chunk {i}/{len(chunks)} added to combined audio")

        except Exception as e:
            logger.error(f"An error occurred for chunk {i}/{len(chunks)}: {e}")
            if "429" in str(e):
                logger.critical("Quota exceeded. Stopping further requests.")
                success = False
                break

    if success and not combined_audio.empty():
        logger.info("All chunks processed successfully, finalizing audio")
        silence = AudioSegment.silent(duration=SILENCE_TIME_MS)
        combined_audio = silence + combined_audio + silence
        logger.debug(f"Silence added at start and end ({SILENCE_TIME_MS}ms)")

        logger.info(f"Exporting audio to {output_path}")
        combined_audio.export(output_path, format=output_format)
        logger.info(f"Audio saved to {output_path}")
    else:
        logger.error("No audio generated due to errors.")
        if output_path.exists():
            logger.warning(f"Removing partial file: {output_path}")
            output_path.unlink()

    logger.info("OpenAI processing completed")
