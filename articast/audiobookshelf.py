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
                logger.error(f"Audiobookshelf API error: {error_data.get('error', error_message)}")
            except json.JSONDecodeError:
                logger.error(f"Audiobookshelf HTTP Error: {e.code} - {error_message}")
            raise Exception(f"Audiobookshelf upload failed: {e.code} - {error_message}")
        except urllib.error.URLError as e:
            logger.error(f"Audiobookshelf URL Error: {e.reason}")
            raise Exception(f"Audiobookshelf connection failed: {e.reason}")
        except Exception as e:
            logger.error(f"Audiobookshelf Error: {str(e)}")
            raise

    def upload_file(self, file_path: Path, library_id: str, folder_id: str, title: Optional[str] = None):
        """Upload a file to a specific library.

        Args:
            file_path: Path to the file to upload
            library_id: ID of the library to upload to
            folder_id: ID of the folder to upload to
            title: Title for the media (optional, defaults to filename)
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File '{file_path}' does not exist.")

        title = title or file_path.stem

        # Use required parameters
        data = {
            "title": title,
            "library": library_id,
            "folder": folder_id,
        }

        # File will be uploaded as "0" parameter
        files = {str(file_path): file_path.name}

        logger.info(f"Uploading to Audiobookshelf:")
        logger.info(f"  URL: {self.base_url}")
        logger.info(f"  Library ID: {library_id}")
        logger.info(f"  Folder ID: {folder_id}")
        logger.info(f"  File: {file_path}")
        logger.info(f"  Title: {title}")

        # Make the API request
        return self.make_request("POST", "/api/upload", data=data, files=files)


def upload_to_audiobookshelf(
    file_path: Path, 
    abs_url: str, 
    abs_pod_lib_id: str, 
    abs_pod_folder_id: str, 
    title: Optional[str] = None
) -> bool:
    """
    Upload an audio file to Audiobookshelf.
    
    Args:
        file_path: Path to the audio file
        abs_url: Audiobookshelf server URL
        abs_pod_lib_id: Podcast library ID
        abs_pod_folder_id: Podcast folder ID
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
        response = client.upload_file(file_path, abs_pod_lib_id, abs_pod_folder_id, title)
        
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
