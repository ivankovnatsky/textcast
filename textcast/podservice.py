"""Podservice integration for uploading audio episodes to podcast feed."""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)


def upload_to_podservice(
    file_path: Path,
    title: str,
    podservice_url: str,
    description: Optional[str] = None,
    source_url: Optional[str] = None,
    image_url: Optional[str] = None,
    timeout: int = 120,
    max_retries: int = 3,
    retry_delay: float = 5.0,
) -> bool:
    """Upload audio file to podservice as a new episode.

    Args:
        file_path: Path to audio file (MP3, etc.)
        title: Episode title
        podservice_url: Base URL of podservice (e.g., http://192.168.50.7:8083)
        description: AI-generated episode summary
        source_url: Original article URL (used as GUID for deduplication)
        image_url: URL to page icon/og:image (podservice downloads it)
        timeout: Request timeout in seconds (default 120 for large files)
        max_retries: Maximum number of retry attempts for connection errors (default 3)
        retry_delay: Delay between retries in seconds (default 5.0)

    Returns:
        True if upload succeeded (including 409 duplicate), False otherwise
    """
    if not file_path.exists():
        logger.error(f"Audio file does not exist: {file_path}")
        return False

    # Normalize URL (remove trailing slash)
    podservice_url = podservice_url.rstrip("/")
    endpoint = f"{podservice_url}/api/episodes"

    last_error = None
    for attempt in range(max_retries):
        if attempt > 0:
            logger.info(f"Retry attempt {attempt + 1}/{max_retries} after {retry_delay}s delay...")
            time.sleep(retry_delay)

        try:
            logger.info(f"Uploading to podservice: {title}")
            logger.debug(f"Endpoint: {endpoint}")
            logger.debug(f"File: {file_path} ({file_path.stat().st_size / 1024 / 1024:.1f} MB)")

            with open(file_path, "rb") as audio_file:
                files = {"audio": (file_path.name, audio_file)}
                data = {
                    "title": title,
                    "description": description or "",
                    "source_url": source_url or "",
                    "pub_date": datetime.now().isoformat(),
                }

                if image_url:
                    data["image_url"] = image_url

                response = requests.post(
                    endpoint,
                    files=files,
                    data=data,
                    timeout=timeout,
                )

            if response.status_code == 201:
                logger.info(f"Successfully uploaded to podservice: {title}")
                try:
                    result = response.json()
                    logger.debug(f"Episode URL: {result.get('episode', {}).get('audio_url', 'N/A')}")
                except Exception:
                    pass
                return True

            elif response.status_code == 409:
                # Episode already exists - this is success, not an error
                logger.info(f"Episode already exists in podservice: {source_url or title}")
                return True

            elif response.status_code == 400:
                # Bad request - don't retry, it won't help
                try:
                    error_msg = response.json().get("error", response.text)
                except Exception:
                    error_msg = response.text
                logger.error(f"Podservice rejected request: {error_msg}")
                return False

            else:
                # Other error - might be transient, continue to retry
                logger.warning(f"Podservice upload failed with status {response.status_code}: {response.text}")
                last_error = f"HTTP {response.status_code}: {response.text}"
                continue

        except requests.Timeout:
            logger.warning(f"Podservice upload timed out after {timeout}s (attempt {attempt + 1}/{max_retries})")
            last_error = f"Timeout after {timeout}s"
            continue

        except requests.ConnectionError as e:
            logger.warning(f"Could not connect to podservice at {podservice_url} (attempt {attempt + 1}/{max_retries}): {e}")
            last_error = str(e)
            continue

        except requests.RequestException as e:
            logger.warning(f"Podservice upload error (attempt {attempt + 1}/{max_retries}): {e}")
            last_error = str(e)
            continue

        except Exception as e:
            logger.error(f"Unexpected error uploading to podservice: {e}", exc_info=True)
            return False

    # All retries exhausted
    logger.error(f"Failed to upload to podservice after {max_retries} attempts. Last error: {last_error}")
    return False
