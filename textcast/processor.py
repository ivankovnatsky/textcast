import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Dict, List, Optional

import click

from .aggregator import detect_and_expand_aggregator
from .audio_scrape import try_scrape_and_download
from .audiobookshelf import download_audio
from .common import process_text_to_audio, upload_to_destinations
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


def _process_single_url(
    url: str, aggregator_sources: Dict[str, str], **kwargs
) -> ProcessingResult:
    """Process a single URL. Thread-safe — no shared mutable state."""
    try:
        output_dir = kwargs.get("directory", "/tmp/textcast")

        # STEP 1: Try yt-dlp (works for YouTube, Substack, and 1000+ sites)
        logger.info(f"Trying yt-dlp for: {url}")
        audio_file = None
        try:
            audio_file = download_audio(url, output_dir)
        except Exception as e:
            logger.debug(f"yt-dlp failed for {url}: {e}")

        if audio_file and audio_file.exists():
            logger.info(f"yt-dlp succeeded for: {url}")
            title = audio_file.stem

            upload_success = upload_to_destinations(
                file_path=audio_file,
                title=title,
                destinations=kwargs.get("destinations"),
                source_url=url,
                abs_url=kwargs.get("abs_url"),
                abs_library=kwargs.get("abs_pod_lib_id"),
                abs_folder_id=kwargs.get("abs_pod_folder_id"),
                podservice_url=kwargs.get("podservice_url"),
            )

            if upload_success:
                logger.info(f"Successfully processed URL via yt-dlp: {url}")

                try:
                    os.remove(audio_file)
                    logger.info(f"Deleted local audio file: {audio_file}")
                except Exception as e:
                    logger.warning(f"Failed to delete local audio file: {e}")

                return ProcessingResult(url=url, success=True)
            else:
                raise ProcessingError(
                    "Failed to upload yt-dlp audio to destinations"
                )

        # STEP 2: Try Playwright scraping (for JS-loaded audio players)
        logger.info(f"yt-dlp failed, trying Playwright scrape for: {url}")
        audio_file, page_title = try_scrape_and_download(url, output_dir)

        if audio_file and audio_file.exists():
            logger.info(f"Playwright scrape succeeded for: {url}")
            title = page_title or audio_file.stem

            upload_success = upload_to_destinations(
                file_path=audio_file,
                title=title,
                destinations=kwargs.get("destinations"),
                source_url=url,
                abs_url=kwargs.get("abs_url"),
                abs_library=kwargs.get("abs_pod_lib_id"),
                abs_folder_id=kwargs.get("abs_pod_folder_id"),
                podservice_url=kwargs.get("podservice_url"),
            )

            if upload_success:
                logger.info(f"Successfully processed URL via Playwright: {url}")

                try:
                    os.remove(audio_file)
                    logger.info(f"Deleted local audio file: {audio_file}")
                except Exception as e:
                    logger.warning(f"Failed to delete local audio file: {e}")

                return ProcessingResult(url=url, success=True)
            else:
                raise ProcessingError(
                    "Failed to upload Playwright audio to destinations"
                )

        # STEP 3: Fall back to TTS
        logger.info(f"No existing audio found, using TTS for: {url}")

        if not filter_url(url):
            logger.info(f"Skipping URL: {url}")
            return ProcessingResult(
                url=url,
                success=False,
                skipped=True,
                error="URL filtered: non-text content",
            )

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
            return ProcessingResult(
                url=url, success=False, skipped=True, error="Skipped by user"
            )

        logger.info(f"Processing text: '{title}' (extracted using {method})")

        if kwargs.get("condense"):
            logger.info("Condensing text...")
            text = condense_text(
                text,
                kwargs["text_model"],
                kwargs["condense_ratio"],
                kwargs.get("text_provider", "openai"),
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
            destinations=kwargs.get("destinations"),
            # Legacy parameters for backward compatibility
            abs_url=kwargs.get("abs_url"),
            abs_pod_lib_id=kwargs.get("abs_pod_lib_id"),
            abs_pod_folder_id=kwargs.get("abs_pod_folder_id"),
            podservice_url=kwargs.get("podservice_url"),
            source_url=url,  # Pass original URL for GUID deduplication
        )

        return ProcessingResult(url=url, success=True)

    except Exception as e:
        logger.error(f"Failed to process {url}: {str(e)}")
        return ProcessingResult(url=url, success=False, error=str(e))


def _update_source_file(
    results: List[ProcessingResult],
    aggregator_sources: Dict[str, str],
    **kwargs,
):
    """Update source file once after all processing is complete."""
    file_url_list = kwargs.get("file_url_list")
    if not file_url_list or not os.path.exists(file_url_list):
        return

    successful_urls = {r.url for r in results if r.success}
    skipped_urls = {r.url for r in results if r.skipped}
    failed_urls = {
        r.url: r.error for r in results if not r.success and not r.skipped
    }

    failed_file = os.path.join(os.path.dirname(file_url_list), "Failed.txt")

    try:
        # Write failed and filtered URLs to Failed.txt
        entries_to_write = []
        for url in skipped_urls:
            result = next(r for r in results if r.url == url)
            entries_to_write.append(f"{url} # {result.error}\n")
        for url, error in failed_urls.items():
            # Don't write aggregator article failures to Failed.txt
            if url not in aggregator_sources:
                entries_to_write.append(f"{url}\n")

        if entries_to_write:
            with open(failed_file, "a") as f:
                for entry in entries_to_write:
                    f.write(entry)

        # Determine which URLs to remove from source file
        urls_to_remove = set()

        # Remove successful and skipped direct URLs
        for url in successful_urls | skipped_urls:
            if url not in aggregator_sources:
                urls_to_remove.add(url)
            else:
                logger.info(
                    f"Processed article from aggregator {aggregator_sources[url]}: {url}"
                )

        # Remove failed direct URLs (they've been moved to Failed.txt)
        for url in failed_urls:
            if url not in aggregator_sources:
                urls_to_remove.add(url)

        # Remove aggregator URLs whose articles have all been processed
        unique_aggregators = set(aggregator_sources.values())
        for aggregator_url in unique_aggregators:
            articles = [
                u for u, agg in aggregator_sources.items() if agg == aggregator_url
            ]
            successful_count = sum(1 for a in articles if a in successful_urls)
            logger.info(
                f"Aggregator {aggregator_url}: processed {successful_count}/{len(articles)} articles"
            )
            urls_to_remove.add(aggregator_url)

        # Rewrite the source file once
        if urls_to_remove:
            with open(file_url_list, "r") as f:
                lines = f.readlines()

            with open(file_url_list, "w") as f:
                for line in lines:
                    if line.strip() not in urls_to_remove:
                        f.write(line)

            logger.info(
                f"Updated {file_url_list}: removed {len(urls_to_remove)} URL(s)"
            )

    except Exception as e:
        logger.error(f"Failed to update source file: {str(e)}")


def process_texts(urls: List[str], **kwargs) -> List[ProcessingResult]:
    """
    Process a list of text URLs, converting them to audio.

    Args:
        urls: List of URLs to process
        **kwargs: Additional arguments from CLI (condense, text_model, condense_ratio, workers, etc.)

    Returns:
        List[ProcessingResult]: Results of processing each text
    """
    workers = kwargs.get("workers", 5)
    auto_detect_aggregator = kwargs.get("auto_detect_aggregator", True)

    # Expand aggregator URLs (sequential — fast, must happen first)
    expanded_urls = []
    aggregator_sources = {}  # Map article URLs to their aggregator source

    for url in urls:
        if auto_detect_aggregator:
            is_aggregator, article_urls = detect_and_expand_aggregator(url)
            if is_aggregator and article_urls:
                logger.info(
                    f"Detected aggregator URL {url}, expanded to {len(article_urls)} articles"
                )
                expanded_urls.extend(article_urls)
                for article_url in article_urls:
                    aggregator_sources[article_url] = url
            else:
                expanded_urls.append(url)
        else:
            expanded_urls.append(url)

    # Auto-approve when using parallel workers (interactive prompts aren't thread-safe)
    if workers > 1 and not kwargs.get("yes"):
        logger.warning(
            "Parallel processing (workers=%d) requires auto-approve, enabling --yes",
            workers,
        )
        kwargs["yes"] = True

    # Process URLs
    if workers == 1:
        # Sequential processing (backward compatible)
        results = []
        for url in expanded_urls:
            result = _process_single_url(url, aggregator_sources, **kwargs)
            results.append(result)
    else:
        # Parallel processing
        logger.info(f"Processing {len(expanded_urls)} URLs with {workers} workers")
        results = []
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_url = {
                executor.submit(
                    _process_single_url, url, aggregator_sources, **kwargs
                ): url
                for url in expanded_urls
            }
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                except Exception as e:
                    logger.error(f"Unexpected error processing {url}: {str(e)}")
                    result = ProcessingResult(url=url, success=False, error=str(e))
                results.append(result)

    # Batch file updates after all processing
    _update_source_file(results, aggregator_sources, **kwargs)

    # Log summary
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
