"""
Service configuration for textcast daemon mode.
"""

import os
import platform
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

import yaml


def parse_interval(value: Union[str, int]) -> int:
    """Parse interval value with required time unit suffix.

    Supports:
    - With units: 30s, 5m, 1h, 2d
    - Legacy support: plain integers (for backward compatibility only)

    Returns interval in minutes.
    """
    if isinstance(value, int):
        # Legacy support - warn but allow
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(
            f"Using bare number {value} for interval is deprecated. Please use time units like '{value}m'"
        )
        return value

    if isinstance(value, str):
        # Try to parse string with time unit
        match = re.match(r"^(\d+)([smhd])$", value.strip().lower())
        if match:
            number, unit = match.groups()
            number = int(number)

            if unit == "s":  # seconds
                return max(1, number // 60)  # Convert to minutes, min 1 minute
            elif unit == "m":  # minutes
                return number
            elif unit == "h":  # hours
                return number * 60
            elif unit == "d":  # days
                return number * 60 * 24

        # Check if it's a bare number string - reject it
        try:
            int(value.strip())
            raise ValueError(
                f"Bare numbers not allowed for intervals. Use '{value}m' instead of '{value}'"
            )
        except ValueError as e:
            if "invalid literal" in str(e):
                # It's not a number, fall through to main error
                pass
            else:
                # It is a number, re-raise our custom error
                raise

    raise ValueError(
        f"Invalid interval format: {value}. Use format like '5m', '1h', '30s' with required time unit."
    )


@dataclass
class SourceConfig:
    """Configuration for a content source."""

    type: str  # rss, youtube, file, upload
    name: str
    enabled: bool = True
    # RSS source fields
    url: Optional[str] = None
    # YouTube source fields
    channel_id: Optional[str] = None
    channel_handle: Optional[str] = None  # Can be @handle, handle, or full URL
    download_dir: Optional[str] = None
    # File source fields
    file: Optional[str] = None
    # Upload source fields
    watch_dir: Optional[str] = None
    file_patterns: List[str] = field(
        default_factory=lambda: ["*.mp3", "*.m4a", "*.wav"]
    )
    # Common fields
    check_duplicates: bool = True
    processing_strategy: Optional[str] = None  # condense, full, or None for default


@dataclass
class ProcessingConfig:
    """Configuration for text processing."""

    strategy: str = "condense"  # condense, full
    condense_ratio: float = 0.5
    text_model: str = "gpt-5.1"
    speech_model: str = "tts-1-hd"
    voice: str = "nova"
    audio_format: str = "mp3"
    output_dir: str = "/tmp/textcast-service"
    vendor: str = "openai"


@dataclass
class AudiobookshelfConfig:
    """Configuration for Audiobookshelf integration."""

    server: str = "http://localhost:13378"
    api_key: str = ""
    library_name: str = ""  # Library name (empty = auto-select first library)
    library_id: str = ""  # Deprecated: use library_name instead
    folder_id: str = ""  # Deprecated: auto-detected when using library_name


@dataclass
class PodserviceConfig:
    """Configuration for Podservice integration (legacy, use destinations instead)."""

    enabled: bool = False
    url: str = ""  # Base URL of podservice (e.g., http://192.168.50.7:8083)


@dataclass
class DestinationConfig:
    """Base configuration for a destination."""

    type: str  # podservice, audiobookshelf
    enabled: bool = True


@dataclass
class PodserviceDestination(DestinationConfig):
    """Configuration for Podservice destination."""

    url: str = ""  # Base URL of podservice


@dataclass
class AudiobookshelfDestination(DestinationConfig):
    """Configuration for Audiobookshelf destination."""

    server: str = ""
    api_key: str = ""
    library_name: str = ""  # Library name (empty = auto-select first library)
    library_id: str = ""  # Deprecated: use library_name instead
    folder_id: str = ""  # Deprecated: auto-detected when using library_name


@dataclass
class ServerConfig:
    """Configuration for web server."""

    enabled: bool = False
    host: str = "127.0.0.1"
    port: int = 8084
    base_url: Optional[str] = None  # Auto-generated if not set


@dataclass
class ServiceConfig:
    """Main service configuration."""

    check_interval: int = 5  # minutes (for external resources: RSS, YouTube)
    file_check_interval: int = 1  # minutes (for local files - more frequent)
    sources: List[SourceConfig] = field(default_factory=list)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    destinations: List[Union[PodserviceDestination, AudiobookshelfDestination]] = field(
        default_factory=list
    )
    # Legacy config fields (deprecated, use destinations instead)
    audiobookshelf: AudiobookshelfConfig = field(default_factory=AudiobookshelfConfig)
    podservice: PodserviceConfig = field(default_factory=PodserviceConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    log_level: str = "INFO"
    log_file: Optional[str] = None


def get_default_config_path() -> Path:
    """Get the default configuration file path."""
    home = Path.home()

    if platform.system() == "Darwin":
        # macOS
        return (
            home
            / "Library"
            / "Application Support"
            / "textcast-service"
            / "config.yaml"
        )
    else:
        # Linux and other Unix-like systems
        return home / ".config" / "textcast-service" / "config.yaml"


def _parse_destinations(
    data: dict,
) -> List[Union[PodserviceDestination, AudiobookshelfDestination]]:
    """Parse destinations list from config data.

    Supports both new 'destinations:' format and legacy 'audiobookshelf:'/'podservice:' blocks.
    """
    import logging

    logger = logging.getLogger(__name__)
    destinations = []

    # Check for new destinations format
    if "destinations" in data:
        for dest_data in data.get("destinations", []):
            dest_type = dest_data.get("type")
            if dest_type == "podservice":
                destinations.append(
                    PodserviceDestination(
                        type="podservice",
                        enabled=dest_data.get("enabled", True),
                        url=dest_data.get("url", ""),
                    )
                )
            elif dest_type == "audiobookshelf":
                # Get api_key from config or environment
                api_key = dest_data.get("api_key", "")
                if not api_key:
                    api_key = os.getenv("ABS_API_KEY", "")
                # Get server from config or environment
                server = dest_data.get("server", "")
                if not server:
                    server = os.getenv("ABS_URL", "")

                destinations.append(
                    AudiobookshelfDestination(
                        type="audiobookshelf",
                        enabled=dest_data.get("enabled", True),
                        server=server,
                        api_key=api_key,
                        library_name=dest_data.get("library_name", ""),
                        library_id=dest_data.get("library_id", ""),
                        folder_id=dest_data.get("folder_id", ""),
                    )
                )
            else:
                logger.warning(f"Unknown destination type: {dest_type}")
        return destinations

    # Legacy format: convert audiobookshelf and podservice blocks to destinations
    has_legacy = False

    # Check for legacy podservice block
    podservice_data = data.get("podservice", {})
    if podservice_data.get("enabled") and podservice_data.get("url"):
        has_legacy = True
        destinations.append(
            PodserviceDestination(
                type="podservice",
                enabled=True,
                url=podservice_data.get("url", ""),
            )
        )

    # Check for legacy audiobookshelf block
    abs_data = data.get("audiobookshelf", {})
    # Get api_key from config or environment
    api_key = abs_data.get("api_key", "")
    if not api_key:
        api_key = os.getenv("ABS_API_KEY", "")
    # Get server from config or environment
    server = abs_data.get("server", "")
    if not server:
        server = os.getenv("ABS_URL", "")

    if server and api_key:
        has_legacy = True
        destinations.append(
            AudiobookshelfDestination(
                type="audiobookshelf",
                enabled=True,
                server=server,
                api_key=api_key,
                library_name=abs_data.get("library_name", ""),
                library_id=abs_data.get("library_id", ""),
                folder_id=abs_data.get("folder_id", ""),
            )
        )

    if has_legacy:
        logger.warning(
            "Using legacy 'audiobookshelf:' and 'podservice:' config format. "
            "Please migrate to new 'destinations:' list format."
        )

    return destinations


def load_config(config_path: Optional[str] = None) -> ServiceConfig:
    """Load service configuration from YAML file."""
    if config_path is None:
        config_path = get_default_config_path()
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        # Return default configuration
        return ServiceConfig()

    try:
        with open(config_path, "r") as f:
            data = yaml.safe_load(f)

        # Parse sources
        sources = []
        for source_data in data.get("sources", []):
            sources.append(SourceConfig(**source_data))

        # Parse processing config
        processing_data = data.get("processing", {})
        processing = ProcessingConfig(**processing_data)

        # Parse destinations (new format with backward compatibility)
        destinations = _parse_destinations(data)

        # Parse legacy audiobookshelf config (for backward compatibility)
        abs_data = data.get("audiobookshelf", {})
        # Use environment variables if not provided in config (only for api_key and server)
        if not abs_data.get("api_key"):
            abs_data["api_key"] = os.getenv("ABS_API_KEY", "")
        if not abs_data.get("server"):
            abs_data["server"] = os.getenv("ABS_URL", "")
        audiobookshelf = AudiobookshelfConfig(**abs_data)

        # Parse server config
        server_data = data.get("server", {})
        server = ServerConfig(**server_data)

        # Parse legacy podservice config (for backward compatibility)
        podservice_data = data.get("podservice", {})
        podservice = PodserviceConfig(**podservice_data)

        # Create main config
        config = ServiceConfig(
            check_interval=parse_interval(data.get("check_interval", "5m")),
            file_check_interval=parse_interval(data.get("file_check_interval", "1m")),
            sources=sources,
            processing=processing,
            destinations=destinations,
            audiobookshelf=audiobookshelf,
            podservice=podservice,
            server=server,
            log_level=data.get("log_level", "INFO"),
            log_file=data.get("log_file"),
        )

        return config

    except Exception as e:
        raise Exception(f"Failed to load configuration from {config_path}: {e}")


def _serialize_destinations(
    destinations: List[Union[PodserviceDestination, AudiobookshelfDestination]],
) -> List[dict]:
    """Serialize destinations list to dict format for YAML."""
    result = []
    for dest in destinations:
        if isinstance(dest, PodserviceDestination):
            result.append(
                {
                    "type": "podservice",
                    "enabled": dest.enabled,
                    "url": dest.url,
                }
            )
        elif isinstance(dest, AudiobookshelfDestination):
            result.append(
                {
                    "type": "audiobookshelf",
                    "enabled": dest.enabled,
                    "server": dest.server,
                    "api_key": dest.api_key,
                    "library_name": dest.library_name,
                    "library_id": dest.library_id,
                    "folder_id": dest.folder_id,
                }
            )
    return result


def save_config(config: ServiceConfig, config_path: Optional[str] = None) -> None:
    """Save service configuration to YAML file."""
    if config_path is None:
        config_path = get_default_config_path()
    else:
        config_path = Path(config_path)

    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dict
    data = {
        "check_interval": config.check_interval,
        "file_check_interval": config.file_check_interval,
        "sources": [
            {
                "type": s.type,
                "name": s.name,
                "enabled": s.enabled,
                "url": s.url,
                "channel_id": s.channel_id,
                "channel_handle": s.channel_handle,
                "download_dir": s.download_dir,
                "file": s.file,
                "watch_dir": s.watch_dir,
                "file_patterns": s.file_patterns,
                "check_duplicates": s.check_duplicates,
                "processing_strategy": s.processing_strategy,
            }
            for s in config.sources
        ],
        "processing": {
            "strategy": config.processing.strategy,
            "condense_ratio": config.processing.condense_ratio,
            "text_model": config.processing.text_model,
            "speech_model": config.processing.speech_model,
            "voice": config.processing.voice,
            "audio_format": config.processing.audio_format,
            "output_dir": config.processing.output_dir,
            "vendor": config.processing.vendor,
        },
        "log_level": config.log_level,
        "log_file": config.log_file,
    }

    # Use new destinations format if destinations are configured
    if config.destinations:
        data["destinations"] = _serialize_destinations(config.destinations)
    else:
        # Fall back to legacy format if no destinations but legacy configs exist
        data["audiobookshelf"] = {
            "server": config.audiobookshelf.server,
            "api_key": config.audiobookshelf.api_key,
            "library_name": config.audiobookshelf.library_name,
            "library_id": config.audiobookshelf.library_id,
            "folder_id": config.audiobookshelf.folder_id,
        }
        data["podservice"] = {
            "enabled": config.podservice.enabled,
            "url": config.podservice.url,
        }

    with open(config_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, indent=2)


def create_example_config(config_path: Optional[str] = None) -> None:
    """Create an example configuration file."""
    # Determine the path
    if config_path is None:
        config_path = get_default_config_path().parent / "config.example.yaml"
    else:
        config_path = Path(config_path)

    # If example config already exists, load it to preserve values like library_name
    existing_abs_config = {}
    if config_path.exists():
        try:
            existing_config = load_config(str(config_path))
            existing_abs_config = {
                "server": existing_config.audiobookshelf.server,
                "library_name": existing_config.audiobookshelf.library_name,
            }
        except Exception:
            pass  # If loading fails, use defaults

    example_config = ServiceConfig(
        check_interval=5,  # Will be saved as 5 for backward compatibility
        sources=[
            SourceConfig(
                type="rss",
                name="sreweekly",
                enabled=True,
                url="https://sreweekly.com/feed",
                processing_strategy="condense",
            ),
            SourceConfig(
                type="youtube",
                name="serhii_sternenko",
                enabled=True,
                channel_handle="@STERNENKO",
                download_dir="/Volumes/Storage/Data/Youtube/",
            ),
            SourceConfig(
                type="file",
                name="textcast_manual",
                enabled=True,
                file="/Volumes/Storage/Data/Textcast/Texts/Texts.txt",
            ),
        ],
        processing=ProcessingConfig(
            strategy="condense",
            condense_ratio=0.5,
            text_model="gpt-5.1",
            speech_model="tts-1-hd",
            voice="nova",
            audio_format="mp3",
            vendor="openai",
        ),
        audiobookshelf=AudiobookshelfConfig(
            server=existing_abs_config.get("server", ""),
            library_name=existing_abs_config.get("library_name", ""),
        ),
        log_level="INFO",
    )

    save_config(example_config, config_path)
