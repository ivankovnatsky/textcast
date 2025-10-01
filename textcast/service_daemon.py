"""
Textcast service daemon for continuous content monitoring and processing.
"""

import logging
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# from .rss_monitor import NewsletterMonitor, YouTubeMonitor
from .processor import process_texts
from .service_config import ServiceConfig, SourceConfig, load_config

logger = logging.getLogger(__name__)


class TextcastService:
    """Main service class for continuous content monitoring and processing."""

    def __init__(self, config: ServiceConfig):
        self.config = config
        self.running = False
        self.monitors: Dict[str, object] = {}
        self.file_watchers = []  # Store file watchers

        # Initialize monitors for each source
        for source in config.sources:
            if not source.enabled:
                continue

            if source.type == "rss":
                logger.warning(
                    f"RSS source '{source.name}' configured but not implemented yet"
                )
            elif source.type == "youtube":
                logger.warning(
                    f"YouTube source '{source.name}' configured but not implemented yet"
                )
            elif source.type == "file":
                # File sources will be monitored by file watchers
                self._setup_file_watcher(source)
            elif source.type == "upload":
                # Upload sources will be monitored by directory watchers
                self._setup_upload_watcher(source)
            else:
                logger.warning(f"Unknown source type: {source.type} for {source.name}")

        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _setup_file_watcher(self, source: SourceConfig):
        """Set up file watcher for a file source."""
        try:
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer
        except ImportError:
            logger.warning(
                "watchdog package not found. File sources will be checked via polling."
            )
            return

        if not source.file or not Path(source.file).exists():
            logger.warning(
                f"File source {source.name}: file {source.file} does not exist"
            )
            return

        file_path = Path(source.file)

        class FileSourceHandler(FileSystemEventHandler):
            def __init__(self, service_ref, source_config):
                self.service = service_ref
                self.source = source_config

            def on_modified(self, event):
                if event.is_directory:
                    return

                # Check if the modified file is our target file
                if Path(event.src_path).resolve() == file_path.resolve():
                    logger.info(
                        f"File source {self.source.name} changed: {event.src_path}"
                    )
                    self.service._process_file_queue(self.source)

        handler = FileSourceHandler(self, source)
        observer = Observer()
        observer.schedule(handler, str(file_path.parent), recursive=False)

        self.file_watchers.append((observer, source.name))
        logger.info(f"Set up file watcher for {source.name}: {source.file}")

    def _setup_upload_watcher(self, source: SourceConfig):
        """Set up directory watcher for an upload source."""
        try:
            import fnmatch

            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer
        except ImportError:
            logger.warning("watchdog package not found. Upload sources will not work.")
            return

        if not source.watch_dir or not Path(source.watch_dir).exists():
            logger.warning(
                f"Upload source {source.name}: directory {source.watch_dir} does not exist"
            )
            return

        watch_path = Path(source.watch_dir)

        class UploadHandler(FileSystemEventHandler):
            def __init__(self, service_ref, source_config):
                self.service = service_ref
                self.source = source_config
                self.pending_files = {}  # Track pending file uploads with timestamps

            def on_created(self, event):
                if event.is_directory:
                    return

                file_path = Path(event.src_path)
                # Check if file matches any of the patterns
                for pattern in self.source.file_patterns:
                    if fnmatch.fnmatch(file_path.name.lower(), pattern.lower()):
                        logger.info(
                            f"Upload source {self.source.name}: new file detected: {file_path}"
                        )

                        # Add debounce delay to prevent immediate processing during file creation
                        import threading
                        import time

                        def delayed_upload():
                            # FIXME: Wait 20 seconds to ensure file is completely written
                            # TODO: Consider implementing a file watcher that waits for file to be written
                            # or some other neat fix instead of hard-coded delay
                            time.sleep(20)

                            # Check if file still exists before processing
                            if file_path.exists():
                                # Check file stability - ensure it hasn't been modified in the last 10 seconds
                                try:
                                    file_mtime = file_path.stat().st_mtime
                                    current_time = time.time()

                                    if current_time - file_mtime < 10:
                                        logger.debug(
                                            f"File {file_path.name} was recently modified, waiting for stability"
                                        )
                                        return

                                    # Check if file is not currently being processed by another event
                                    file_key = str(file_path)

                                    # Skip if this file was recently processed (within 10 seconds)
                                    if (
                                        file_key in self.pending_files
                                        and current_time - self.pending_files[file_key]
                                        < 10
                                    ):
                                        logger.debug(
                                            f"Skipping {file_path.name} - recently processed"
                                        )
                                        return

                                    # Mark file as being processed
                                    self.pending_files[file_key] = current_time

                                    logger.info(
                                        f"File {file_path.name} is stable, proceeding with upload"
                                    )
                                    self.service._upload_to_audiobookshelf(
                                        file_path, self.source
                                    )

                                    # Clean up old entries to prevent memory leaks
                                    old_entries = [
                                        k
                                        for k, v in self.pending_files.items()
                                        if current_time - v > 60
                                    ]
                                    for k in old_entries:
                                        del self.pending_files[k]

                                except OSError as e:
                                    logger.debug(
                                        f"Error checking file {file_path.name}: {e}"
                                    )
                                    return
                            else:
                                logger.debug(
                                    f"File {file_path.name} no longer exists, skipping upload"
                                )

                        # Start delayed upload in background thread
                        threading.Thread(target=delayed_upload, daemon=True).start()
                        break

        handler = UploadHandler(self, source)
        observer = Observer()
        observer.schedule(handler, str(watch_path), recursive=True)

        self.file_watchers.append((observer, source.name))
        logger.info(
            f"Set up upload watcher for {source.name}: {source.watch_dir} (patterns: {source.file_patterns})"
        )

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()

    def start(self):
        """Start the service daemon."""
        logger.info("Starting Textcast service daemon...")

        # Show user-friendly interval
        interval_min = self.config.check_interval
        if interval_min < 60:
            interval_str = f"{interval_min}m"
        elif interval_min < 1440:  # Less than a day
            hours = interval_min // 60
            remaining_min = interval_min % 60
            if remaining_min == 0:
                interval_str = f"{hours}h"
            else:
                interval_str = f"{hours}h{remaining_min}m"
        else:  # Days
            days = interval_min // 1440
            remaining_min = interval_min % 1440
            if remaining_min == 0:
                interval_str = f"{days}d"
            else:
                remaining_hours = remaining_min // 60
                remaining_min = remaining_min % 60
                interval_str = f"{days}d{remaining_hours}h" + (
                    f"{remaining_min}m" if remaining_min else ""
                )

        enabled_sources = [s.name for s in self.config.sources if s.enabled]
        external_sources = []
        file_sources = [
            s.name for s in self.config.sources if s.enabled and s.type == "file"
        ]
        upload_sources = [
            s.name for s in self.config.sources if s.enabled and s.type == "upload"
        ]

        # Only show interval if external sources are enabled
        if external_sources:
            logger.info(f"External sources check interval: {interval_str}")

        logger.info(f"Enabled sources: {enabled_sources}")
        logger.info(f"External sources (polled): {external_sources}")
        logger.info(f"File sources (watched): {file_sources}")
        logger.info(f"Upload sources (watched): {upload_sources}")

        self.running = True

        try:
            # Start file watchers
            for observer, source_name in self.file_watchers:
                observer.start()
                logger.info(f"Started file watcher for {source_name}")

            # Initial check of external sources (only if any are enabled)
            if external_sources:
                self._check_external_sources()

            # Process existing file sources once
            for source in self.config.sources:
                if source.enabled and source.type == "file":
                    self._process_file_queue(source)

            # Process existing files in upload directories once
            for source in self.config.sources:
                if source.enabled and source.type == "upload":
                    self._process_existing_upload_files(source)

            # Main loop (only for external sources if any enabled)
            if external_sources:
                while self.running:
                    next_check = time.time() + (self.config.check_interval * 60)

                    while time.time() < next_check and self.running:
                        time.sleep(1)  # Check every second if we should stop

                    if self.running:
                        self._check_external_sources()
            else:
                logger.info(
                    "No external sources enabled, entering idle mode (file/upload watchers active)"
                )
                # Just wait for file watchers to do their work
                while self.running:
                    time.sleep(1)

        except KeyboardInterrupt:
            logger.info("Service interrupted by user")
        except Exception as e:
            logger.error(f"Service error: {e}", exc_info=True)
        finally:
            # Stop file watchers
            for observer, source_name in self.file_watchers:
                observer.stop()
                observer.join()
                logger.info(f"Stopped file watcher for {source_name}")
            logger.info("Textcast service daemon stopped")

    def stop(self):
        """Stop the service daemon."""
        self.running = False

    def _check_external_sources(self):
        """Check external sources (RSS, YouTube) for new content."""
        return

    def _check_all_sources(self):
        """Check all configured sources for new content (legacy method for compatibility)."""
        logger.info(f"Checking all sources at {datetime.now()}")

        for source in self.config.sources:
            if not source.enabled:
                continue

            try:
                self._check_source(source)
            except Exception as e:
                logger.error(f"Error checking source {source.name}: {e}", exc_info=True)

    def _check_source(self, source: SourceConfig):
        """Check a single source for new content."""
        logger.debug(f"Checking source: {source.name} ({source.type})")

        if source.type in ("rss", "youtube"):
            logger.warning(f"Source type {source.type} not implemented yet")
            return

        elif source.type == "file":
            # File source - process existing queue
            self._process_file_queue(source)

    def _process_urls_directly(self, urls: List[str], source: SourceConfig):
        """Process URLs directly without using intermediate files."""
        if not urls:
            return

        logger.info(f"Processing {len(urls)} URLs from {source.name}")

        # Prepare processing arguments
        processing_config = self.config.processing
        source_strategy = source.processing_strategy or processing_config.strategy

        kwargs = {
            "vendor": processing_config.vendor,
            "directory": processing_config.output_dir,
            "audio_format": processing_config.audio_format,
            "speech_model": processing_config.speech_model,
            "text_model": processing_config.text_model,
            "voice": processing_config.voice,
            "strip": None,
            "yes": True,  # Auto-approve processing
            "debug": False,
            "condense": source_strategy == "condense",
            "condense_ratio": processing_config.condense_ratio,
            "aggregator": False,
            "auto_detect_aggregator": True,
        }

        # Add Audiobookshelf settings
        if self.config.audiobookshelf.server and self.config.audiobookshelf.api_key:
            kwargs.update(
                {
                    "abs_url": self.config.audiobookshelf.server,
                    "abs_pod_lib_id": self.config.audiobookshelf.library_id,
                    "abs_pod_folder_id": self.config.audiobookshelf.folder_id,
                }
            )

        # Process the URLs
        results = process_texts(urls, **kwargs)

        # Log results
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        logger.info(
            f"Processing complete for {source.name}: {successful} successful, {failed} failed"
        )

    def _process_file_queue(self, source: SourceConfig):
        """Process URLs from a file queue using textcast processing."""
        if not Path(source.file).exists():
            logger.debug(f"Queue file does not exist: {source.file}")
            return

        try:
            # Read URLs from queue
            with open(source.file, "r") as f:
                urls = []
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # Handle CSV format (url,strategy)
                        url_parts = line.split(",")
                        urls.append(url_parts[0])

            if not urls:
                logger.debug(f"No URLs to process in {source.file}")
                return

            logger.info(f"Processing {len(urls)} URLs from {source.name}")

            # Prepare processing arguments based on source and global config
            processing_config = self.config.processing
            source_strategy = source.processing_strategy or processing_config.strategy

            kwargs = {
                "file_url_list": source.file,
                "vendor": processing_config.vendor,
                "directory": processing_config.output_dir,
                "audio_format": processing_config.audio_format,
                "speech_model": processing_config.speech_model,
                "text_model": processing_config.text_model,
                "voice": processing_config.voice,
                "strip": None,
                "yes": True,  # Auto-approve processing
                "debug": False,
                "condense": source_strategy == "condense",
                "condense_ratio": processing_config.condense_ratio,
                "aggregator": False,
                "auto_detect_aggregator": True,
            }

            # Add Audiobookshelf settings
            if self.config.audiobookshelf.server and self.config.audiobookshelf.api_key:
                kwargs.update(
                    {
                        "abs_url": self.config.audiobookshelf.server,
                        "abs_pod_lib_id": self.config.audiobookshelf.library_id,
                        "abs_pod_folder_id": self.config.audiobookshelf.folder_id,
                    }
                )

            # Process the URLs
            results = process_texts(urls, **kwargs)

            # Log results
            successful = sum(1 for r in results if r.success)
            failed = len(results) - successful

            logger.info(
                f"Processing complete for {source.name}: {successful} successful, {failed} failed"
            )

        except Exception as e:
            logger.error(f"Error processing queue {source.file}: {e}", exc_info=True)

    def _upload_to_audiobookshelf(self, file_path: Path, source: SourceConfig):
        """Upload audio file to Audiobookshelf."""
        if not self.config.audiobookshelf.server:
            logger.warning(
                f"Audiobookshelf server not configured, cannot upload {file_path}"
            )
            return

        if not self.config.audiobookshelf.library_id:
            logger.warning(
                f"Audiobookshelf library_id not configured, cannot upload {file_path}"
            )
            return

        if not self.config.audiobookshelf.folder_id:
            logger.warning(
                f"Audiobookshelf folder_id not configured, cannot upload {file_path}"
            )
            return

        try:
            # Import audiobookshelf module
            from .audiobookshelf import upload_to_audiobookshelf

            logger.info(f"Uploading {file_path.name} to Audiobookshelf...")

            # Upload the file (API key comes from environment variable)
            success = upload_to_audiobookshelf(
                file_path,  # Pass Path object, not string
                self.config.audiobookshelf.server,
                self.config.audiobookshelf.library_id,
                self.config.audiobookshelf.folder_id,
                title=file_path.stem,  # Use filename without extension as title
            )

            if success:
                logger.info(f"Successfully uploaded {file_path.name} to Audiobookshelf")

                # Delete the file after successful upload
                if file_path.exists():
                    try:
                        file_path.unlink()
                        logger.info(f"Deleted uploaded file: {file_path.name}")
                    except Exception as e:
                        logger.warning(
                            f"Failed to delete uploaded file {file_path.name}: {e}"
                        )
                else:
                    logger.debug(
                        f"File {file_path.name} already deleted (likely by another handler)"
                    )
            else:
                logger.error(f"Failed to upload {file_path.name} to Audiobookshelf")

        except ImportError:
            logger.error("Audiobookshelf module not found. Cannot upload files.")
        except Exception as e:
            logger.error(
                f"Error uploading {file_path.name} to Audiobookshelf: {e}",
                exc_info=True,
            )

    def _process_existing_upload_files(self, source: SourceConfig):
        """Process existing files in upload directory on service start."""
        if not source.watch_dir or not Path(source.watch_dir).exists():
            logger.debug(
                f"Upload source {source.name}: directory {source.watch_dir} does not exist"
            )
            return

        try:

            watch_path = Path(source.watch_dir)
            existing_files = []

            # Find all matching files recursively
            for pattern in source.file_patterns:
                files = list(watch_path.rglob(pattern))
                existing_files.extend(files)

            if existing_files:
                logger.info(
                    f"Found {len(existing_files)} existing files in {source.name} upload directory"
                )

                for file_path in existing_files:
                    if file_path.is_file():  # Make sure it's actually a file
                        logger.info(f"Processing existing file: {file_path.name}")
                        self._upload_to_audiobookshelf(file_path, source)
            else:
                logger.debug(
                    f"No existing files found in {source.name} upload directory"
                )

        except Exception as e:
            logger.error(
                f"Error processing existing upload files for {source.name}: {e}",
                exc_info=True,
            )


def run_service(
    config_path: str = None, foreground: bool = False, log_file: str = None
):
    """Run the textcast service daemon."""
    # Load configuration
    try:
        config = load_config(config_path)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)

    # Set up logging
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Override log file if provided via CLI
    effective_log_file = log_file or config.log_file

    handlers = []

    # Always add console handler in foreground mode
    if foreground:
        handlers.append(logging.StreamHandler())

    # Add file handler if log file specified
    if effective_log_file:
        try:
            # Ensure log directory exists
            log_path = Path(effective_log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            handlers.append(logging.FileHandler(effective_log_file))
        except Exception as e:
            print(f"Warning: Could not setup log file {effective_log_file}: {e}")

    # Add console handler if no file handler and not foreground
    if not handlers:
        handlers.append(logging.StreamHandler())

    # Configure logging
    logging.basicConfig(level=log_level, format=log_format, handlers=handlers)

    logger.info(
        f"Textcast service starting in {'foreground' if foreground else 'daemon'} mode"
    )
    if effective_log_file:
        logger.info(f"Logging to file: {effective_log_file}")

    # Create and start service
    service = TextcastService(config)
    service.start()


def check_sources_once(config_path: str = None):
    """Check all sources once and exit (useful for testing/debugging)."""
    # Load configuration
    try:
        config = load_config(config_path)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)

    # Set up logging
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create service and check once
    service = TextcastService(config)
    service._check_all_sources()

    logger.info("Single check complete")


if __name__ == "__main__":
    run_service()
