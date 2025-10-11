"""
Audiobookshelf client for uploading audio files.
"""

import json
import logging
import os
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

        raise Exception(f"Library '{library_name}' not found. Available libraries: {[lib.get('name') for lib in libs]}")

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
        library: str,
        folder_id: Optional[str] = None,
        title: Optional[str] = None,
    ):
        """Upload a file to a specific library.

        Args:
            file_path: Path to the file to upload
            library: Library name (e.g., "Podcasts") or library ID (UUID)
            folder_id: ID of the folder to upload to (optional, auto-detected if library is a name)
            title: Title for the media (optional, defaults to filename)
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File '{file_path}' does not exist.")

        title = title or file_path.stem

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
    library: str,
    folder_id: Optional[str] = None,
    title: Optional[str] = None,
) -> bool:
    """
    Upload an audio file to Audiobookshelf.

    Args:
        file_path: Path to the audio file
        abs_url: Audiobookshelf server URL
        library: Library name (e.g., "Podcasts") or library ID (UUID)
        folder_id: Optional folder ID (auto-detected if library is a name)
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
        response = client.upload_file(
            file_path, library, folder_id, title
        )

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
