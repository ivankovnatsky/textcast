"""
Service CLI commands for textcast daemon mode.
"""

import logging
import signal
import subprocess
import sys
import time
from pathlib import Path

import click

from .service_config import create_example_config, get_default_config_path, load_config
from .service_daemon import check_sources_once, run_service

logger = logging.getLogger(__name__)


@click.group()
@click.option("--config", type=click.Path(), help="Path to configuration file")
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.pass_context
def service(ctx, config, debug):
    """Textcast service daemon commands."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = config
    ctx.obj["debug"] = debug

    # Set up logging
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


@service.command()
@click.option("--config", type=click.Path(), help="Path to configuration file")
@click.option(
    "--foreground",
    "-f",
    is_flag=True,
    help="Run in foreground mode (default: daemon mode)",
)
@click.option("--log-file", type=click.Path(), help="Log file path (overrides config)")
@click.option(
    "--no-watch",
    is_flag=True,
    help="Disable config file watching (watching enabled by default)",
)
@click.pass_context
def daemon(ctx, config, foreground, log_file, no_watch):
    """Run textcast service in daemon mode with automatic config file watching."""
    # Use command-line config if provided, otherwise fall back to group-level config
    config_path = config or ctx.obj.get("config")

    # Enable watching by default, disable only if explicitly requested
    watch_config = not no_watch

    if watch_config and foreground:
        click.echo(
            "Starting textcast service in foreground mode with config watching..."
        )
        _run_service_with_watcher(config_path, log_file)
    else:
        if foreground:
            click.echo("Starting textcast service in foreground mode...")
        else:
            click.echo("Starting textcast service daemon...")

        if watch_config and not foreground:
            click.echo("⚠️  Config watching only available in foreground mode")

        run_service(config_path, foreground=foreground, log_file=log_file)


@service.command()
@click.option("--config", type=click.Path(), help="Path to configuration file")
@click.pass_context
def check(ctx, config):
    """Check all sources once and exit."""
    config_path = config or ctx.obj.get("config")
    click.echo("Checking all sources once...")
    check_sources_once(config_path)


@service.command()
@click.option("--output", type=click.Path(), help="Output path for example config")
@click.pass_context
def init_config(ctx, output):
    """Create an example configuration file."""
    if output:
        config_path = Path(output)
    else:
        config_path = get_default_config_path().parent / "config.example.yaml"

    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    create_example_config(str(config_path))
    click.echo(f"Example configuration created at: {config_path}")
    click.echo("Copy this to your config directory and customize as needed.")


@service.command()
@click.option("--config", type=click.Path(), help="Path to configuration file")
@click.pass_context
def status(ctx, config):
    """Show service configuration and status."""
    config_path = config or ctx.obj.get("config")

    try:
        config = load_config(config_path)
        click.echo("Textcast Service Configuration:")
        click.echo(f"Check interval: {config.check_interval} minutes")
        click.echo(f"Log level: {config.log_level}")

        if config.log_file:
            click.echo(f"Log file: {config.log_file}")

        click.echo(f"\nSources ({len(config.sources)} configured):")
        for source in config.sources:
            status = "enabled" if source.enabled else "disabled"
            click.echo(f"  - {source.name} ({source.type}): {status}")

            if source.type == "rss":
                click.echo(f"    URL: {source.url}")
            elif source.type == "youtube":
                if source.channel_handle:
                    click.echo(f"    Channel: {source.channel_handle}")
                elif source.channel_id:
                    click.echo(f"    Channel ID: {source.channel_id}")
                if source.download_dir:
                    click.echo(f"    Download dir: {source.download_dir}")
            elif source.type == "file":
                click.echo(f"    File: {source.file}")
            elif source.type == "upload":
                click.echo(f"    Watch dir: {source.watch_dir}")
                click.echo(f"    File patterns: {source.file_patterns}")

        click.echo("\nProcessing:")
        click.echo(f"  Strategy: {config.processing.strategy}")
        click.echo(f"  Vendor: {config.processing.vendor}")
        click.echo(f"  Model: {config.processing.speech_model}")
        click.echo(f"  Voice: {config.processing.voice}")

        if config.audiobookshelf.server and config.audiobookshelf.api_key:
            click.echo("\nAudiobookshelf:")
            click.echo(f"  Server: {config.audiobookshelf.server}")
            click.echo(f"  Library ID: {config.audiobookshelf.library_id}")
        else:
            click.echo("\nAudiobookshelf: not configured (server/api_key missing)")

    except Exception as e:
        click.echo(f"Error loading configuration: {e}", err=True)


@service.command()
@click.option("--config", type=click.Path(), help="Path to configuration file")
@click.argument("source_name")
@click.pass_context
def test_source(ctx, config, source_name):
    """Test a specific source configuration."""
    config_path = config or ctx.obj.get("config")

    try:
        config = load_config(config_path)

        # Find the source
        source = None
        for s in config.sources:
            if s.name == source_name:
                source = s
                break

        if not source:
            click.echo(f"Source '{source_name}' not found in configuration", err=True)
            return

        click.echo(f"Testing source: {source.name} ({source.type})")

        if source.type == "rss":
            from .rss_monitor import NewsletterMonitor

            monitor = NewsletterMonitor(source)
            urls = monitor.check_for_new_content()
            click.echo(f"Found {len(urls)} URLs:")
            for url in urls[:10]:  # Show first 10
                click.echo(f"  - {url}")
            if len(urls) > 10:
                click.echo(f"  ... and {len(urls) - 10} more")

        elif source.type == "youtube":
            from .rss_monitor import YouTubeMonitor

            monitor = YouTubeMonitor(source)
            urls = monitor.check_for_new_content()
            click.echo(f"Found {len(urls)} videos:")
            for url in urls:
                click.echo(f"  - {url}")

        elif source.type == "file":
            file_path = Path(source.file)
            if file_path.exists():
                with open(file_path, "r") as f:
                    urls = [
                        line.strip()
                        for line in f
                        if line.strip() and not line.startswith("#")
                    ]
                click.echo(f"File contains {len(urls)} URLs")
            else:
                click.echo("File does not exist")

        elif source.type == "upload":
            watch_dir = Path(source.watch_dir) if source.watch_dir else None
            if watch_dir and watch_dir.exists():
                all_files = []
                for pattern in source.file_patterns:
                    files = list(watch_dir.rglob(pattern))
                    all_files.extend(files)

                click.echo(f"Watch directory contains {len(all_files)} matching files:")
                for f in all_files[:10]:  # Show first 10
                    click.echo(f"  - {f.name}")
                if len(all_files) > 10:
                    click.echo(f"  ... and {len(all_files) - 10} more")
            else:
                click.echo("Watch directory does not exist")

    except Exception as e:
        click.echo(f"Error testing source: {e}", err=True)


def _run_service_with_watcher(config_path, log_file=None):
    """Run service with config file watching."""
    # Use example config by default if none specified
    if not config_path:
        config_path = "config.example.yaml"

    # Create example config if it doesn't exist
    if not Path(config_path).exists():
        click.echo("📝 Creating example configuration...")
        create_example_config(config_path)

    config_path = Path(config_path)

    if not config_path.exists():
        click.echo(f"❌ Config file not found: {config_path}", err=True)
        click.echo("💡 Run 'textcast service init-config' to create one")
        return

    click.echo(f"📁 Using config: {config_path}")

    # Show absolute path for clarity
    watch_dir = config_path.parent.resolve()
    click.echo(f"👀 Watching: {watch_dir}")
    click.echo("💡 Edit the config file to see the service restart automatically")
    click.echo("🔄 Press Ctrl+C to stop")
    click.echo("")

    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError:
        click.echo("❌ watchdog package not found. Please install it:", err=True)
        click.echo("pip install watchdog", err=True)
        return

    class ServiceHandler(FileSystemEventHandler):
        def __init__(self):
            self.process = None
            self.restart_service()

        def on_modified(self, event):
            if event.is_directory:
                return

            # Only restart on config file changes
            if event.src_path.endswith(".yaml") or event.src_path.endswith(".yml"):
                click.echo(f"\n📝 Config file changed: {event.src_path}")
                click.echo("🔄 Restarting service...")
                self.restart_service()

        def restart_service(self):
            # Stop existing process
            if self.process:
                click.echo("🛑 Stopping current service...")
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()

            # Start new process
            click.echo(f"🚀 Starting service with config: {config_path}")
            cmd = [
                sys.executable,
                "-m",
                "textcast",
                "service",
                "--config",
                str(config_path),
                "daemon",
                "--foreground",
                "--no-watch",
            ]

            if log_file:
                cmd.extend(["--log-file", str(log_file)])

            try:
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1,
                )

                # Print output in real-time
                import threading

                def print_output():
                    for line in iter(self.process.stdout.readline, ""):
                        if line:
                            click.echo(f"📋 {line.rstrip()}")

                output_thread = threading.Thread(target=print_output, daemon=True)
                output_thread.start()

            except Exception as e:
                click.echo(f"❌ Failed to start service: {e}", err=True)

        def stop(self):
            if self.process:
                click.echo("🛑 Stopping service...")
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()

    # Set up file watcher
    handler = ServiceHandler()
    observer = Observer()
    observer.schedule(handler, str(config_path.parent), recursive=False)

    # Handle Ctrl+C gracefully
    def signal_handler(signum, frame):
        click.echo("\n🛑 Received interrupt signal")
        handler.stop()
        observer.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # Start watching
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)
    finally:
        observer.stop()
        observer.join()


@service.command()
@click.pass_context
def watch(ctx):
    """Legacy command - use 'daemon --foreground' instead (watching is now enabled by default)."""
    click.echo("💡 The 'watch' command is deprecated.")
    click.echo(
        "🎯 Use 'textcast service daemon --foreground' instead (watching is now enabled by default)"
    )

    # Forward to daemon command for compatibility
    ctx.invoke(daemon, foreground=True, log_file=None, no_watch=False)


# Add service command to main CLI
def add_service_commands(main_cli):
    """Add service commands to the main CLI."""
    main_cli.add_command(service)
