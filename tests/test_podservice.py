"""Tests for podservice integration."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from textcast.podservice import upload_to_podservice


class TestUploadToPodservice:
    """Tests for the upload_to_podservice function."""

    def test_upload_success(self):
        """Test successful upload returns True."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"fake audio data")
            audio_path = Path(f.name)

        try:
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.json.return_value = {
                "success": True,
                "episode": {"audio_url": "http://localhost:8083/audio/test.mp3"},
            }

            with patch("textcast.podservice.requests.post", return_value=mock_response):
                result = upload_to_podservice(
                    file_path=audio_path,
                    title="Test Episode",
                    podservice_url="http://localhost:8083",
                    source_url="https://example.com/article",
                )

            assert result is True
        finally:
            audio_path.unlink()

    def test_upload_duplicate_returns_true(self):
        """Test that 409 Conflict (duplicate) returns True."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"fake audio data")
            audio_path = Path(f.name)

        try:
            mock_response = MagicMock()
            mock_response.status_code = 409
            mock_response.json.return_value = {
                "success": True,
                "message": "Episode already exists",
            }

            with patch("textcast.podservice.requests.post", return_value=mock_response):
                result = upload_to_podservice(
                    file_path=audio_path,
                    title="Test Episode",
                    podservice_url="http://localhost:8083",
                    source_url="https://example.com/article",
                )

            assert result is True
        finally:
            audio_path.unlink()

    def test_upload_bad_request_returns_false(self):
        """Test that 400 Bad Request returns False."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"fake audio data")
            audio_path = Path(f.name)

        try:
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.json.return_value = {"success": False, "error": "Missing title"}
            mock_response.text = "Missing title"

            with patch("textcast.podservice.requests.post", return_value=mock_response):
                result = upload_to_podservice(
                    file_path=audio_path,
                    title="",
                    podservice_url="http://localhost:8083",
                )

            assert result is False
        finally:
            audio_path.unlink()

    def test_upload_server_error_returns_false(self):
        """Test that 500 Server Error returns False."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"fake audio data")
            audio_path = Path(f.name)

        try:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"

            with patch("textcast.podservice.requests.post", return_value=mock_response):
                result = upload_to_podservice(
                    file_path=audio_path,
                    title="Test Episode",
                    podservice_url="http://localhost:8083",
                )

            assert result is False
        finally:
            audio_path.unlink()

    def test_upload_connection_error_returns_false(self):
        """Test that connection errors return False."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"fake audio data")
            audio_path = Path(f.name)

        try:
            import requests

            with patch(
                "textcast.podservice.requests.post",
                side_effect=requests.ConnectionError("Connection refused"),
            ):
                result = upload_to_podservice(
                    file_path=audio_path,
                    title="Test Episode",
                    podservice_url="http://localhost:8083",
                )

            assert result is False
        finally:
            audio_path.unlink()

    def test_upload_timeout_returns_false(self):
        """Test that timeouts return False."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"fake audio data")
            audio_path = Path(f.name)

        try:
            import requests

            with patch(
                "textcast.podservice.requests.post",
                side_effect=requests.Timeout("Request timed out"),
            ):
                result = upload_to_podservice(
                    file_path=audio_path,
                    title="Test Episode",
                    podservice_url="http://localhost:8083",
                )

            assert result is False
        finally:
            audio_path.unlink()

    def test_upload_nonexistent_file_returns_false(self):
        """Test that nonexistent file returns False."""
        result = upload_to_podservice(
            file_path=Path("/nonexistent/file.mp3"),
            title="Test Episode",
            podservice_url="http://localhost:8083",
        )

        assert result is False

    def test_upload_url_normalization(self):
        """Test that trailing slashes are removed from URL."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"fake audio data")
            audio_path = Path(f.name)

        try:
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.json.return_value = {"success": True, "episode": {}}

            with patch("textcast.podservice.requests.post", return_value=mock_response) as mock_post:
                upload_to_podservice(
                    file_path=audio_path,
                    title="Test Episode",
                    podservice_url="http://localhost:8083/",  # Trailing slash
                )

                # Verify the URL was normalized (no trailing slash)
                call_args = mock_post.call_args
                assert call_args[0][0] == "http://localhost:8083/api/episodes"
        finally:
            audio_path.unlink()

    def test_upload_includes_all_metadata(self):
        """Test that all metadata fields are sent correctly."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"fake audio data")
            audio_path = Path(f.name)

        try:
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.json.return_value = {"success": True, "episode": {}}

            with patch("textcast.podservice.requests.post", return_value=mock_response) as mock_post:
                upload_to_podservice(
                    file_path=audio_path,
                    title="Test Episode",
                    podservice_url="http://localhost:8083",
                    description="Test description",
                    source_url="https://example.com/article",
                    image_url="https://example.com/image.png",
                )

                call_args = mock_post.call_args
                data = call_args[1]["data"]

                assert data["title"] == "Test Episode"
                assert data["description"] == "Test description"
                assert data["source_url"] == "https://example.com/article"
                assert data["image_url"] == "https://example.com/image.png"
                assert "pub_date" in data
        finally:
            audio_path.unlink()
