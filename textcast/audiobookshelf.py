"""
Audiobookshelf client for uploading audio files.
"""

import json
import logging
import os
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class AudiobookshelfClient:
    """Client for interacting with the Audiobookshelf API."""

    def __init__(self, api_key: str, base_url: str):
        """Initialize the client with API key and base URL."""
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def get_libraries(self):
        """Fetch all libraries from Audiobookshelf."""
        return self.make_request("GET", "/api/libraries")

    def get_default_library(self):
        """Get first available library and its first folder (zero-config mode).

        Returns:
            dict with 'library_id' and 'folder_id' keys

        Raises:
            Exception if no libraries found
        """
        libraries = self.get_libraries()

        if not libraries or not isinstance(libraries, dict):
            raise Exception("Failed to fetch libraries from Audiobookshelf")

        libs = libraries.get("libraries", [])

        if not libs:
            raise Exception("No libraries found in Audiobookshelf")

        # Use first library
        lib = libs[0]
        library_id = lib.get("id")
        library_name = lib.get("name")
        folders = lib.get("folders", [])

        if not folders:
            raise Exception(f"Library '{library_name}' has no folders")

        folder_id = folders[0].get("id")

        logger.info(f"Auto-selected first library '{library_name}': {library_id}")
        logger.info(f"Using first folder: {folder_id}")

        return {
            "library_id": library_id,
            "folder_id": folder_id,
        }

    def get_library_by_name(self, library_name: str):
        """Get library ID and first folder ID by library name.

        Args:
            library_name: Name of the library to find

        Returns:
            dict with 'library_id' and 'folder_id' keys

        Raises:
            Exception if library not found
        """
        libraries = self.get_libraries()

        if not libraries or not isinstance(libraries, dict):
            raise Exception("Failed to fetch libraries from Audiobookshelf")

        # libraries response has a 'libraries' key with array of library objects
        libs = libraries.get("libraries", [])

        for lib in libs:
            if lib.get("name") == library_name:
                library_id = lib.get("id")
                folders = lib.get("folders", [])

                if not folders:
                    raise Exception(f"Library '{library_name}' has no folders")

                folder_id = folders[0].get("id")

                logger.info(f"Found library '{library_name}': {library_id}")
                logger.info(f"Using first folder: {folder_id}")

                return {
                    "library_id": library_id,
                    "folder_id": folder_id,
                }

        raise Exception(
            f"Library '{library_name}' not found. Available libraries: {[lib.get('name') for lib in libs]}"
        )

    def make_request(self, method: str, endpoint: str, data=None, files=None):
        """Make an HTTP request to the Audiobookshelf API."""
        url = f"{self.base_url}{endpoint}"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            if files:
                # Handle file uploads with multipart/form-data
                boundary = "----boundary" + str(int(time.time()))
                headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"

                # Create multipart body
                body = []

                # Add regular form fields
                if data:
                    for key, value in data.items():
                        body.append(f"--{boundary}".encode())
                        body.append(
                            f'Content-Disposition: form-data; name="{key}"'.encode()
                        )
                        body.append(b"")
                        body.append(str(value).encode())

                # Add file as '0' parameter (matching curl's -F 0=@file.mp3 format)
                for i, (file_path, file_name) in enumerate(files.items()):
                    body.append(f"--{boundary}".encode())
                    body.append(
                        f'Content-Disposition: form-data; name="{i}"; filename="{file_name}"'.encode()
                    )
                    body.append(b"Content-Type: application/octet-stream")
                    body.append(b"")

                    with open(file_path, "rb") as file:
                        body.append(file.read())

                # Close the multipart body
                body.append(f"--{boundary}--".encode())
                body.append(b"")

                # Join with CRLF as per HTTP spec
                data = b"\r\n".join(body)
                request = urllib.request.Request(
                    url, data=data, headers=headers, method=method
                )

            elif data:
                # For regular JSON requests
                headers["Content-Type"] = "application/json"
                json_data = json.dumps(data).encode("utf-8")
                request = urllib.request.Request(
                    url, data=json_data, headers=headers, method=method
                )
            else:
                # Simple GET request
                request = urllib.request.Request(url, headers=headers, method=method)

            # Send the request and handle the response
            with urllib.request.urlopen(request) as response:
                response_data = response.read().decode("utf-8")
                if not response_data:
                    return None

                try:
                    return json.loads(response_data)
                except json.JSONDecodeError:
                    return response_data

        except urllib.error.HTTPError as e:
            # Handle HTTP errors (4xx, 5xx)
            error_message = e.read().decode("utf-8")
            try:
                error_data = json.loads(error_message)
                logger.error(
                    f"Audiobookshelf API error: {error_data.get('error', error_message)}"
                )
            except json.JSONDecodeError:
                logger.error(f"Audiobookshelf HTTP Error: {e.code} - {error_message}")
            raise Exception(f"Audiobookshelf upload failed: {e.code} - {error_message}")
        except urllib.error.URLError as e:
            logger.error(f"Audiobookshelf URL Error: {e.reason}")
            raise Exception(f"Audiobookshelf connection failed: {e.reason}")
        except Exception as e:
            logger.error(f"Audiobookshelf Error: {str(e)}")
            raise

    def upload_file(
        self,
        file_path: Path,
        library: Optional[str] = None,
        folder_id: Optional[str] = None,
        title: Optional[str] = None,
    ):
        """Upload a file to a specific library.

        Args:
            file_path: Path to the file to upload
            library: Library name (e.g., "Podcasts") or library ID (UUID). If not specified, uses first available library.
            folder_id: ID of the folder to upload to (optional, auto-detected)
            title: Title for the media (optional, defaults to filename)
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File '{file_path}' does not exist.")

        title = title or file_path.stem

        # Zero-config mode: no library specified, use first available
        if not library:
            logger.info("No library specified, auto-selecting first available library")
            lib_info = self.get_default_library()
            library_id = lib_info["library_id"]
            folder_id = lib_info["folder_id"]
        else:
            # Determine if library is a name or ID
            # UUIDs are 36 chars with dashes (e.g., "db54da2c-dc16-4fdb-8dd4-5375ae98f738")
            is_library_id = len(library) == 36 and "-" in library

            if is_library_id:
                # Using library ID directly - folder_id must be provided
                if not folder_id:
                    raise ValueError("folder_id is required when using library ID")
                library_id = library
            else:
                # Using library name - look it up and auto-detect folder
                logger.info(f"Looking up library by name: {library}")
                lib_info = self.get_library_by_name(library)
                library_id = lib_info["library_id"]
                folder_id = lib_info["folder_id"]

        # Use required parameters
        data = {
            "title": title,
            "library": library_id,
            "folder": folder_id,
        }

        # File will be uploaded as "0" parameter
        files = {str(file_path): file_path.name}

        logger.info("Uploading to Audiobookshelf:")
        logger.info(f"  URL: {self.base_url}")
        logger.info(f"  Library: {library} -> {library_id}")
        logger.info(f"  Folder ID: {folder_id}")
        logger.info(f"  File: {file_path}")
        logger.info(f"  Title: {title}")

        # Make the API request
        return self.make_request("POST", "/api/upload", data=data, files=files)


def upload_to_audiobookshelf(
    file_path: Path,
    abs_url: str,
    library: Optional[str] = None,
    folder_id: Optional[str] = None,
    title: Optional[str] = None,
) -> bool:
    """
    Upload an audio file to Audiobookshelf.

    Args:
        file_path: Path to the audio file
        abs_url: Audiobookshelf server URL
        library: Library name (e.g., "Podcasts") or library ID (UUID). If not specified, uses first available library.
        folder_id: Optional folder ID (auto-detected)
        title: Optional title for the upload

    Returns:
        bool: True if upload was successful, False otherwise
    """
    try:
        # Get API key from environment
        api_key = os.environ.get("ABS_API_KEY")
        if not api_key:
            logger.error("ABS_API_KEY environment variable not set")
            return False

        # Create client and upload
        client = AudiobookshelfClient(api_key, abs_url)
        response = client.upload_file(file_path, library, folder_id, title)

        if response:
            logger.info("Successfully uploaded to Audiobookshelf!")
            logger.debug(f"Response: {response}")
            return True
        else:
            logger.error("Upload to Audiobookshelf failed - no response")
            return False

    except Exception as e:
        logger.error(f"Failed to upload to Audiobookshelf: {str(e)}")
        return False


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
        output_dir = Path(tempfile.mkdtemp(prefix="audiobookshelf-"))
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
                logger.error(msg)

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

        logger.error("No MP3 file was generated.")
        return None

    except Exception as e:
        logger.error(f"Error downloading audio: {str(e)}")
        return None


def process_url_to_audiobookshelf(
    url: str,
    abs_url: str,
    library: Optional[str] = None,
    folder_id: Optional[str] = None,
) -> bool:
    """Download audio from URL and upload to Audiobookshelf.

    Args:
        url: URL to download audio from
        abs_url: Audiobookshelf server URL
        library: Library name or ID (optional)
        folder_id: Folder ID (optional)

    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Processing media URL: {url}")

    # Download audio to temporary directory
    mp3_file = download_audio(url)

    if not mp3_file:
        logger.error("Failed to download audio")
        return False

    try:
        # Upload to Audiobookshelf
        logger.info("Uploading to Audiobookshelf...")
        success = upload_to_audiobookshelf(
            mp3_file,
            abs_url,
            library=library,
            folder_id=folder_id,
            title=mp3_file.stem,
        )

        return success

    finally:
        # Clean up temporary file
        try:
            if mp3_file.exists():
                mp3_file.unlink()
                logger.debug(f"Cleaned up temporary file: {mp3_file}")
                # Also try to remove the temp directory if it's empty
                if mp3_file.parent.name.startswith("audiobookshelf-"):
                    try:
                        mp3_file.parent.rmdir()
                    except OSError:
                        pass  # Directory not empty or other error, ignore
        except Exception as e:
            logger.warning(f"Failed to clean up temporary file: {e}")
