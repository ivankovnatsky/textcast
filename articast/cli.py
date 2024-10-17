import click
import logging
from .article import get_article_content
from .common import (
    generate_lowercase_string,
    validate_models,
    validate_voice,
    process_text_to_audio,
)

logger = logging.getLogger(__name__)


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
    "--file-text",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Path to a file with text to be sent over to AI vendor. This is currently a workaround of Cloudflare blocking.",
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
    ElevenLabs voices: Sarah.
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
@click.option("--yes", is_flag=True, help="Automatically answer yes to all prompts")
@click.option("--debug", is_flag=True, help="Enable debug logging")
def cli(
    vendor,
    url,
    file_url_list,
    file_text,
    directory,
    audio_format,
    model,
    voice,
    strip,
    yes,
    debug,
):
    # Set up logging
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger(__name__)

    logger.debug("Starting CLI with options: %s", locals())

    if not url and not file_url_list and not file_text:
        raise click.UsageError(
            "You must provide either --url, --file-url-list or --file-text."
        )

    # Set model and voice based on the API vendor
    if vendor == "elevenlabs":
        model = model or "eleven_monolingual_v1"
        voice = voice or "Sarah"
    elif vendor == "openai":
        model = model or "tts-1"
        voice = voice or "alloy"

    logger.debug("Using vendor: %s, model: %s, voice: %s", vendor, model, voice)

    if file_text:
        with open(file_text, "r") as f:
            text = f.read()
        title = f"custom-text-podcast-{generate_lowercase_string()}"
        logger.info(f"Processing custom text with title: {title}")
        process_text_to_audio(
            text, title, vendor, directory, audio_format, model, voice, strip
        )
    else:
        urls = []
        if url:
            urls.append(url)
        if file_url_list:
            with open(file_url_list, "r") as f:
                urls.extend([line.strip() for line in f if line.strip()])

        for url in urls:
            logger.info(f"Fetching content from URL: {url}")
            text, title = get_article_content(url)
            logger.info(f"Retrieved article with title: '{title}'")

            if yes or click.confirm(
                f"Do you want to proceed with converting '{title}' to audio?"
            ):
                logger.info(f"Processing article: '{title}'")
                process_text_to_audio(
                    text, title, vendor, directory, audio_format, model, voice, strip
                )
            else:
                logger.info(f"Skipping article: '{title}'")


if __name__ == "__main__":
    cli()
