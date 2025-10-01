import logging
import os
from dataclasses import dataclass
from typing import List, Optional

import click

from .common import process_text_to_audio
from .condense import condense_text
from .constants import MIN_CONTENT_LENGTH, SUSPICIOUS_TEXTS
from .errors import ProcessingError
from .filter_urls import filter_url
from .text import get_text_content

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    url: str
    success: bool
    skipped: bool = False
    error: Optional[str] = None
    text: Optional[str] = None
    title: Optional[str] = None
    method: Optional[str] = None


def process_texts(urls: List[str], **kwargs) -> List[ProcessingResult]:
    """
    Process a list of text URLs, converting them to audio.

    Args:
        urls: List of URLs to process
        **kwargs: Additional arguments from CLI (condense, text_model, condense_ratio, etc.)

    Returns:
        List[ProcessingResult]: Results of processing each text
    """
    results = []
    aggregator_source = kwargs.get("aggregator_source")

    for url in urls:
        try:
            if not filter_url(url):
                logger.info(f"Skipping URL: {url}")
                results.append(
                    ProcessingResult(
                        url=url,
                        success=False,
                        skipped=True,
                        error="URL filtered: non-text content",
                    )
                )

                # Move filtered URL to failed file
                file_url_list = kwargs.get("file_url_list")
                if file_url_list and os.path.exists(file_url_list):
                    try:
                        # Determine failed file path
                        failed_file = os.path.join(
                            os.path.dirname(file_url_list), "Failed.txt"
                        )

                        # Add to failed file with reason
                        with open(failed_file, "a") as f:
                            f.write(f"{url} # Filtered: non-text content\n")

                        # Remove from original file
                        with open(file_url_list, "r") as f:
                            lines = f.readlines()

                        with open(file_url_list, "w") as f:
                            for line in lines:
                                if line.strip() != url:
                                    f.write(line)

                        logger.info(f"Moved filtered URL to {failed_file}: {url}")
                    except Exception as file_e:
                        logger.error(
                            f"Failed to move filtered URL to failed file: {str(file_e)}"
                        )

                continue

            logger.info(f"Fetching content from URL: {url}")
            text, title, method = get_text_content(url)

            logger.debug(
                f"Content extracted using {method} ({len(text)} chars):\n---\n{text}\n---"
            )

            # Check for suspicious content patterns
            text_lower = text.lower()
            for suspicious in SUSPICIOUS_TEXTS:
                if suspicious in text_lower:
                    raise ProcessingError(
                        f"Suspicious content detected: '{suspicious}'. Text may not have loaded properly."
                    )

            if len(text) < MIN_CONTENT_LENGTH:
                raise ProcessingError(
                    f"Content too short ({len(text)} chars). Text may not have loaded properly."
                )

            if not kwargs.get("yes") and not click.confirm(
                f"Do you want to proceed with converting '{title}' to audio?",
                default=False,
            ):
                results.append(
                    ProcessingResult(
                        url=url, success=False, skipped=True, error="Skipped by user"
                    )
                )

                # Remove skipped URL from original file (user chose not to process)
                file_url_list = kwargs.get("file_url_list")
                if file_url_list and os.path.exists(file_url_list):
                    try:
                        with open(file_url_list, "r") as f:
                            lines = f.readlines()

                        with open(file_url_list, "w") as f:
                            for line in lines:
                                if line.strip() != url:
                                    f.write(line)

                        logger.info(
                            f"Removed user-skipped URL from {file_url_list}: {url}"
                        )
                    except Exception as file_e:
                        logger.error(
                            f"Failed to remove user-skipped URL: {str(file_e)}"
                        )

                continue

            logger.info(f"Processing text: '{title}' (extracted using {method})")

            if kwargs.get("condense"):
                logger.info("Condensing text...")
                text = condense_text(
                    text, kwargs["text_model"], kwargs["condense_ratio"]
                )

            # Process the text to audio
            process_text_to_audio(
                text=text,
                title=title,
                vendor=kwargs["vendor"],
                directory=kwargs["directory"],
                audio_format=kwargs["audio_format"],
                model=kwargs["speech_model"],
                voice=kwargs["voice"],
                strip=kwargs["strip"],
                abs_url=kwargs.get("abs_url"),
                abs_pod_lib_id=kwargs.get("abs_pod_lib_id"),
                abs_pod_folder_id=kwargs.get("abs_pod_folder_id"),
            )

            results.append(ProcessingResult(url=url, success=True))

            # Remove successfully processed URL from the file immediately
            file_url_list = kwargs.get("file_url_list")
            aggregator_source = kwargs.get("aggregator_source")

            if file_url_list and os.path.exists(file_url_list):
                try:
                    with open(file_url_list, "r") as f:
                        lines = f.readlines()

                    # If this came from an aggregator, we need to remove the aggregator URL
                    # only when all articles are processed (this is handled elsewhere)
                    # For now, just log appropriately
                    if aggregator_source:
                        # Don't remove individual article URLs, they weren't in the file
                        logger.info(
                            f"Processed article from aggregator {aggregator_source}: {url}"
                        )
                    else:
                        # Remove the URL from the file (it was directly in the file)
                        with open(file_url_list, "w") as f:
                            for line in lines:
                                if line.strip() != url:
                                    f.write(line)
                        logger.info(
                            f"Removed successfully processed URL from {file_url_list}: {url}"
                        )
                except Exception as e:
                    logger.error(
                        f"Failed to update URL file after processing {url}: {str(e)}"
                    )

        except Exception as e:
            logger.error(f"Failed to process {url}: {str(e)}")
            results.append(ProcessingResult(url=url, success=False, error=str(e)))

            # Move failed URL to failed file
            file_url_list = kwargs.get("file_url_list")
            if file_url_list and os.path.exists(file_url_list):
                try:
                    # Determine failed file path
                    failed_file = os.path.join(
                        os.path.dirname(file_url_list), "Failed.txt"
                    )

                    # Add to failed file
                    with open(failed_file, "a") as f:
                        f.write(f"{url}\n")

                    # Remove from original file
                    with open(file_url_list, "r") as f:
                        lines = f.readlines()

                    with open(file_url_list, "w") as f:
                        for line in lines:
                            if line.strip() != url:
                                f.write(line)

                    logger.info(f"Moved failed URL to {failed_file}: {url}")
                except Exception as file_e:
                    logger.error(
                        f"Failed to move failed URL to failed file: {str(file_e)}"
                    )

            continue

    # Remove aggregator URL from file after all articles are processed
    if aggregator_source:
        file_url_list = kwargs.get("file_url_list")
        if file_url_list and os.path.exists(file_url_list):
            try:
                with open(file_url_list, "r") as f:
                    lines = f.readlines()

                with open(file_url_list, "w") as f:
                    for line in lines:
                        if line.strip() != aggregator_source:
                            f.write(line)

                # Count successful articles from this aggregator
                successful_from_aggregator = sum(1 for r in results if r.success)
                logger.info(
                    f"Removed aggregator URL from {file_url_list} after processing {successful_from_aggregator} articles: {aggregator_source}"
                )
            except Exception as e:
                logger.error(f"Failed to remove aggregator URL from file: {str(e)}")

    # Update summary to include skipped count
    successful = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success and not r.skipped)
    skipped = sum(1 for r in results if r.skipped)

    logger.info("Processing Summary:")
    logger.info(f"Successfully processed: {successful}")
    logger.info(f"Failed to process: {failed}")
    logger.info(f"Skipped: {skipped}")

    if failed > 0 or skipped > 0:
        logger.info("Failed texts:")
        for result in results:
            if not result.success and not result.skipped:
                logger.info(f"- {result.url}: {result.error}")

        logger.info("Skipped texts:")
        for result in results:
            if result.skipped:
                logger.info(f"- {result.url}: {result.error}")

    return results
