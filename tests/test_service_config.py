"""Tests for service configuration, including destinations parsing."""

import tempfile
from pathlib import Path

import pytest
import yaml

from textcast.service_config import (
    AudiobookshelfDestination,
    PodserviceDestination,
    ServiceConfig,
    load_config,
    save_config,
)


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for config files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestDestinationsParsing:
    """Test parsing of destinations from config files."""

    def test_load_new_destinations_format(self, temp_config_dir):
        """Test loading config with new destinations format."""
        config_path = Path(temp_config_dir) / "config.yaml"
        config_data = {
            "check_interval": "5m",
            "sources": [],
            "processing": {"strategy": "condense"},
            "destinations": [
                {
                    "type": "podservice",
                    "enabled": True,
                    "url": "http://localhost:8083",
                },
                {
                    "type": "audiobookshelf",
                    "enabled": True,
                    "server": "http://localhost:13378",
                    "api_key": "test-api-key",
                    "library_name": "Podcasts",
                },
            ],
        }

        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        config = load_config(str(config_path))

        assert len(config.destinations) == 2

        # Check podservice destination
        pod_dest = config.destinations[0]
        assert isinstance(pod_dest, PodserviceDestination)
        assert pod_dest.type == "podservice"
        assert pod_dest.enabled is True
        assert pod_dest.url == "http://localhost:8083"

        # Check audiobookshelf destination
        abs_dest = config.destinations[1]
        assert isinstance(abs_dest, AudiobookshelfDestination)
        assert abs_dest.type == "audiobookshelf"
        assert abs_dest.enabled is True
        assert abs_dest.server == "http://localhost:13378"
        assert abs_dest.api_key == "test-api-key"
        assert abs_dest.library_name == "Podcasts"

    def test_load_legacy_format_podservice(self, temp_config_dir, monkeypatch):
        """Test loading config with legacy podservice format."""
        # Clear environment variables to avoid picking up real credentials
        monkeypatch.delenv("ABS_API_KEY", raising=False)
        monkeypatch.delenv("ABS_URL", raising=False)

        config_path = Path(temp_config_dir) / "config.yaml"
        config_data = {
            "check_interval": "5m",
            "sources": [],
            "processing": {"strategy": "condense"},
            "podservice": {
                "enabled": True,
                "url": "http://localhost:8083",
            },
        }

        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        config = load_config(str(config_path))

        # Should convert legacy format to destinations
        assert len(config.destinations) == 1

        pod_dest = config.destinations[0]
        assert isinstance(pod_dest, PodserviceDestination)
        assert pod_dest.url == "http://localhost:8083"
        assert pod_dest.enabled is True

    def test_load_legacy_format_audiobookshelf(self, temp_config_dir, monkeypatch):
        """Test loading config with legacy audiobookshelf format."""
        # Set environment variables for API key and URL
        monkeypatch.setenv("ABS_API_KEY", "env-api-key")
        monkeypatch.setenv("ABS_URL", "")

        config_path = Path(temp_config_dir) / "config.yaml"
        config_data = {
            "check_interval": "5m",
            "sources": [],
            "processing": {"strategy": "condense"},
            "audiobookshelf": {
                "server": "http://localhost:13378",
                "library_name": "Podcasts",
            },
        }

        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        config = load_config(str(config_path))

        # Should convert legacy format to destinations
        assert len(config.destinations) == 1

        abs_dest = config.destinations[0]
        assert isinstance(abs_dest, AudiobookshelfDestination)
        assert abs_dest.server == "http://localhost:13378"
        assert abs_dest.api_key == "env-api-key"
        assert abs_dest.library_name == "Podcasts"

    def test_load_legacy_format_both(self, temp_config_dir, monkeypatch):
        """Test loading config with both legacy formats."""
        monkeypatch.setenv("ABS_API_KEY", "test-key")

        config_path = Path(temp_config_dir) / "config.yaml"
        config_data = {
            "check_interval": "5m",
            "sources": [],
            "processing": {"strategy": "condense"},
            "podservice": {
                "enabled": True,
                "url": "http://localhost:8083",
            },
            "audiobookshelf": {
                "server": "http://localhost:13378",
                "library_name": "Podcasts",
            },
        }

        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        config = load_config(str(config_path))

        # Should convert both legacy formats to destinations
        assert len(config.destinations) == 2

        # Podservice should be first
        pod_dest = config.destinations[0]
        assert isinstance(pod_dest, PodserviceDestination)
        assert pod_dest.url == "http://localhost:8083"

        # Audiobookshelf should be second
        abs_dest = config.destinations[1]
        assert isinstance(abs_dest, AudiobookshelfDestination)
        assert abs_dest.server == "http://localhost:13378"

    def test_destinations_disabled(self, temp_config_dir):
        """Test that disabled destinations are parsed correctly."""
        config_path = Path(temp_config_dir) / "config.yaml"
        config_data = {
            "check_interval": "5m",
            "sources": [],
            "processing": {"strategy": "condense"},
            "destinations": [
                {
                    "type": "podservice",
                    "enabled": False,
                    "url": "http://localhost:8083",
                },
            ],
        }

        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        config = load_config(str(config_path))

        assert len(config.destinations) == 1
        assert config.destinations[0].enabled is False

    def test_empty_destinations(self, temp_config_dir):
        """Test loading config with empty destinations list."""
        config_path = Path(temp_config_dir) / "config.yaml"
        config_data = {
            "check_interval": "5m",
            "sources": [],
            "processing": {"strategy": "condense"},
            "destinations": [],
        }

        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        config = load_config(str(config_path))

        assert len(config.destinations) == 0


class TestDestinationsSerialization:
    """Test serialization of destinations to config files."""

    def test_save_destinations_format(self, temp_config_dir):
        """Test saving config with destinations format."""
        config_path = Path(temp_config_dir) / "config.yaml"

        config = ServiceConfig(
            destinations=[
                PodserviceDestination(
                    type="podservice",
                    enabled=True,
                    url="http://localhost:8083",
                ),
                AudiobookshelfDestination(
                    type="audiobookshelf",
                    enabled=True,
                    server="http://localhost:13378",
                    api_key="test-key",
                    library_name="Podcasts",
                ),
            ],
        )

        save_config(config, str(config_path))

        # Load raw YAML to verify structure
        with open(config_path, "r") as f:
            saved_data = yaml.safe_load(f)

        assert "destinations" in saved_data
        assert len(saved_data["destinations"]) == 2

        # Verify podservice destination
        pod_dest = saved_data["destinations"][0]
        assert pod_dest["type"] == "podservice"
        assert pod_dest["url"] == "http://localhost:8083"

        # Verify audiobookshelf destination
        abs_dest = saved_data["destinations"][1]
        assert abs_dest["type"] == "audiobookshelf"
        assert abs_dest["server"] == "http://localhost:13378"

    def test_save_empty_destinations_uses_legacy(self, temp_config_dir):
        """Test that saving config without destinations uses legacy format."""
        config_path = Path(temp_config_dir) / "config.yaml"

        config = ServiceConfig()  # No destinations

        save_config(config, str(config_path))

        # Load raw YAML to verify structure
        with open(config_path, "r") as f:
            saved_data = yaml.safe_load(f)

        # Should have legacy format when no destinations
        assert "audiobookshelf" in saved_data
        assert "podservice" in saved_data
        assert "destinations" not in saved_data

    def test_roundtrip_destinations(self, temp_config_dir):
        """Test that destinations survive a save/load roundtrip."""
        config_path = Path(temp_config_dir) / "config.yaml"

        original_config = ServiceConfig(
            destinations=[
                PodserviceDestination(
                    type="podservice",
                    enabled=True,
                    url="http://localhost:8083",
                ),
                AudiobookshelfDestination(
                    type="audiobookshelf",
                    enabled=False,
                    server="http://localhost:13378",
                    api_key="test-key",
                    library_name="Podcasts",
                    library_id="lib-123",
                    folder_id="folder-456",
                ),
            ],
        )

        save_config(original_config, str(config_path))
        loaded_config = load_config(str(config_path))

        assert len(loaded_config.destinations) == 2

        # Check podservice
        pod_dest = loaded_config.destinations[0]
        assert pod_dest.url == "http://localhost:8083"
        assert pod_dest.enabled is True

        # Check audiobookshelf
        abs_dest = loaded_config.destinations[1]
        assert abs_dest.server == "http://localhost:13378"
        assert abs_dest.api_key == "test-key"
        assert abs_dest.library_name == "Podcasts"
        assert abs_dest.library_id == "lib-123"
        assert abs_dest.folder_id == "folder-456"
        assert abs_dest.enabled is False
