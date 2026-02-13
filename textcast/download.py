"""
Audio download using yt-dlp.
"""

import logging
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def download_audio(url: str, output_dir: Optional[Path] = None) -> Optional[Path]:
    """Download audio from a URL using yt-dlp library.

    Args:
        url: URL to download from
        output_dir: Directory to save the file to (default: temp directory)

    Returns:
        Path to the downloaded MP3 file or None if failed
    """
    try:
        import yt_dlp
    except ImportError:
        logger.error("yt-dlp library not found. Install with: pip install yt-dlp")
        return None

    logger.info(f"Downloading and extracting audio from {url}...")

    # Create a temporary directory if none provided
    if not output_dir:
        output_dir = Path(tempfile.mkdtemp(prefix="textcast-download-"))
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Configure yt-dlp to use Python logging instead of stdout
        class YtDlpLogger:
            def debug(self, msg):
                # Skip progress messages
                if msg.startswith("[download]"):
                    return
                logger.debug(msg)

            def info(self, msg):
                logger.info(msg)

            def warning(self, msg):
                logger.warning(msg)

            def error(self, msg):
                logger.warning(msg)

        ydl_opts = {
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                },
                {
                    "key": "FFmpegMetadata",
                },
            ],
            "postprocessor_args": ["-ac", "1", "-ar", "24000"],
            "outtmpl": str(output_dir / "%(title)s.%(ext)s"),
            "quiet": True,
            "no_warnings": False,
            "logger": YtDlpLogger(),
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            # Get the output filename
            if info:
                title = info.get("title", "audio")
                # yt-dlp will create the file with .mp3 extension after post-processing
                mp3_file = output_dir / f"{title}.mp3"

                if mp3_file.exists():
                    logger.info(f"Audio extraction completed. File: {mp3_file}")
                    return mp3_file
                else:
                    # Try to find any mp3 file in the output directory
                    mp3_files = list(output_dir.glob("*.mp3"))
                    if mp3_files:
                        logger.info(f"Audio extraction completed. File: {mp3_files[0]}")
                        return mp3_files[0]

        logger.warning("No MP3 file was generated.")
        return None

    except Exception as e:
        logger.warning(f"Error downloading audio: {str(e)}")
        return None
