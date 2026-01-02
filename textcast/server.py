"""HTTP server for adding URLs via web interface."""

import logging
import threading

from flask import Flask, redirect, request

from .common import process_text_to_audio
from .condense import condense_text
from .service_config import ServiceConfig

logger = logging.getLogger(__name__)


class TextcastServer:
    """HTTP server for web-based URL submission."""

    def __init__(self, config: ServiceConfig):
        self.config = config
        self.app = Flask(__name__)
        self._setup_routes()
        self.server_thread = None

    def _get_texts_file(self) -> str:
        """Get the path to the Texts.txt file from the first file source."""
        for source in self.config.sources:
            if source.type == "file" and source.enabled and source.file:
                return source.file
        raise ValueError("No enabled file source found in configuration")

    def _render_debug_result(
        self,
        title: str,
        original_text: str,
        processed_text: str,
        original_word_count: int,
        processed_word_count: int,
        ratio: float,
        model: str,
        provider: str,
        strategy: str,
        target_ratio: float,
    ) -> str:
        """Render the debug result page showing condensed text."""
        import html

        escaped_original = html.escape(original_text)
        escaped_processed = html.escape(processed_text)

        return f"""
        <html>
        <head>
            <title>Debug Result - {html.escape(title)}</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1200px; margin: 50px auto; padding: 20px; background-color: #fff; color: #333; }}
                h1 {{ color: #333; }}
                h2 {{ color: #333; margin-top: 30px; }}
                .back-link {{ margin-bottom: 20px; }}
                .back-link a {{ color: #007bff; text-decoration: none; }}
                .back-link a:hover {{ text-decoration: underline; }}
                .stats {{ background-color: #f8f9fa; padding: 15px; border-radius: 4px; margin-bottom: 20px; }}
                .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; }}
                .stat {{ text-align: center; }}
                .stat-value {{ font-size: 24px; font-weight: bold; color: #007bff; }}
                .stat-label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
                .text-container {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
                .text-box {{ border: 1px solid #ddd; border-radius: 4px; padding: 15px; }}
                .text-box h3 {{ margin-top: 0; color: #333; }}
                .text-content {{ white-space: pre-wrap; font-family: inherit; line-height: 1.6; max-height: 500px; overflow-y: auto; background-color: #fafafa; padding: 10px; border-radius: 4px; }}
                .good {{ color: #28a745; }}
                .warning {{ color: #ffc107; }}
                .bad {{ color: #dc3545; }}

                @media (prefers-color-scheme: dark) {{
                    body {{ background-color: #1a1a1a; color: #e0e0e0; }}
                    h1, h2 {{ color: #e0e0e0; }}
                    .text-box h3 {{ color: #e0e0e0; }}
                    .stats {{ background-color: #2a2a2a; }}
                    .stat-label {{ color: #999; }}
                    .text-box {{ border-color: #444; }}
                    .text-content {{ background-color: #2a2a2a; }}
                    .back-link a {{ color: #4a9eff; }}
                }}

                @media (max-width: 768px) {{
                    .text-container {{ grid-template-columns: 1fr; }}
                    body {{ margin: 20px auto; padding: 15px; }}
                }}
            </style>
        </head>
        <body>
            <div class="back-link"><a href="/">&larr; Back to Textcast</a></div>
            <h1>Debug Result</h1>
            <h2>{html.escape(title)}</h2>

            <div class="stats">
                <div class="stats-grid">
                    <div class="stat">
                        <div class="stat-value">{provider}</div>
                        <div class="stat-label">Provider</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{model}</div>
                        <div class="stat-label">Model</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{strategy}</div>
                        <div class="stat-label">Strategy</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{target_ratio:.0%}</div>
                        <div class="stat-label">Target Ratio</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{original_word_count:,}</div>
                        <div class="stat-label">Original Words</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{processed_word_count:,}</div>
                        <div class="stat-label">Processed Words</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value {"good" if abs(ratio - target_ratio) < 0.1 else "warning" if abs(ratio - target_ratio) < 0.2 else "bad"}">{ratio:.1%}</div>
                        <div class="stat-label">Actual Ratio</div>
                    </div>
                </div>
            </div>

            <div class="text-container">
                <div class="text-box">
                    <h3>Original Text</h3>
                    <div class="text-content">{escaped_original}</div>
                </div>
                <div class="text-box">
                    <h3>Processed Text</h3>
                    <div class="text-content">{escaped_processed}</div>
                </div>
            </div>
        </body>
        </html>
        """

    def _setup_routes(self):
        """Setup Flask routes."""

        @self.app.route("/", methods=["GET"])
        def index():
            """Root endpoint."""
            success = request.args.get("success")
            success_text = request.args.get("success_text")
            error = request.args.get("error")

            message = ""
            if success_text:
                message = '<div style="padding: 10px; background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; border-radius: 4px; margin-bottom: 20px;">✓ Text submitted for processing! Audio will be generated in the background.</div>'
            elif success:
                message = '<div style="padding: 10px; background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; border-radius: 4px; margin-bottom: 20px;">✓ URL added successfully! Processing will start automatically.</div>'
            elif error:
                message = f'<div style="padding: 10px; background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; border-radius: 4px; margin-bottom: 20px;">✗ Error: {error}</div>'

            return f"""
            <html>
            <head>
                <title>Textcast</title>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; background-color: #fff; color: #333; }}
                    h1 {{ color: #333; }}
                    h2 {{ color: #333; }}
                    p {{ color: #666; }}
                    .form-group {{ margin: 40px 0 20px 0; padding-top: 30px; border-top: 1px solid #eee; }}
                    .input-wrapper {{ position: relative; display: flex; gap: 10px; }}
                    input[type="text"], textarea {{ flex: 1; padding: 12px; font-size: 16px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; background-color: #fff; color: #333; }}
                    button {{ background-color: #007bff; color: white; padding: 12px 24px; font-size: 16px; border: none; border-radius: 4px; cursor: pointer; white-space: nowrap; }}
                    button:hover {{ background-color: #0056b3; }}
                    .info {{ margin: 20px 0; padding: 15px; background-color: #f8f9fa; border-left: 4px solid #007bff; }}
                    .info ul {{ margin: 10px 0; padding-left: 20px; }}
                    .info li {{ margin: 5px 0; }}

                    /* Dark mode */
                    @media (prefers-color-scheme: dark) {{
                        body {{ background-color: #1a1a1a; color: #e0e0e0; }}
                        h1, h2 {{ color: #e0e0e0; }}
                        p {{ color: #999; }}
                        .form-group {{ border-top-color: #333; }}
                        input[type="text"], textarea {{ background-color: #2a2a2a; color: #e0e0e0; border-color: #444; }}
                        button {{ background-color: #0d6efd; }}
                        button:hover {{ background-color: #0b5ed7; }}
                        .info {{ background-color: #2a2a2a; border-left-color: #4a9eff; }}
                    }}

                    /* Mobile styles */
                    @media (max-width: 768px) {{
                        body {{ margin: 20px auto; padding: 15px; }}
                        h1 {{ font-size: 24px; }}
                        h2 {{ font-size: 20px; }}
                        .input-wrapper {{ flex-direction: column; gap: 10px; }}
                        input[type="text"] {{ width: 100%; padding: 14px; font-size: 16px; }}
                        button {{ width: 100%; padding: 14px; font-size: 16px; }}
                    }}
                </style>
            </head>
            <body>
                <h1>Textcast</h1>
                <p>Text to Audio Conversion Service</p>

                {message}

                <div class="info">
                    <h2>What happens when you add a URL:</h2>
                    <ul>
                        <li>✨ Text content is extracted from the article</li>
                        <li>🤖 Content is optionally condensed using AI</li>
                        <li>🎙️ Converted to audio using text-to-speech</li>
                        <li>📚 Automatically uploaded to Audiobookshelf</li>
                    </ul>
                    <p><strong>Newsletter URLs are detected automatically!</strong> Articles will be extracted and processed individually.</p>
                </div>

                <div class="form-group">
                    <h2>Add URL</h2>
                    <p style="color: #666; margin-bottom: 15px;">Process article or newsletter URLs. YouTube URLs are converted directly to audio without text-to-speech.</p>
                    <form method="POST" action="/add-url">
                        <div class="input-wrapper">
                            <input type="text" name="url" placeholder="Paste URL here..." required>
                            <button type="submit">Process</button>
                        </div>
                    </form>
                </div>

                <div class="form-group">
                    <h2>Add Free Text</h2>
                    <p style="color: #666; margin-bottom: 15px;">Paste article text directly when URL extraction fails.</p>
                    <form method="POST" action="/add-text">
                        <div style="margin-bottom: 15px;">
                            <input type="text" name="title" placeholder="Article title (required)" required style="width: 100%; margin-bottom: 10px;">
                            <textarea name="text" placeholder="Paste article text here..." required style="width: 100%; min-height: 200px; font-family: inherit; resize: vertical;"></textarea>
                        </div>
                        <div style="margin-bottom: 15px;">
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                                <input type="checkbox" name="debug" value="1" style="width: 18px; height: 18px;">
                                <span>Debug mode (show condensed text, skip audio)</span>
                            </label>
                        </div>
                        <button type="submit">Process Text</button>
                    </form>
                </div>
            </body>
            </html>
            """

        @self.app.route("/add-url", methods=["POST"])
        def add_url():
            """Add a URL to the texts file."""
            try:
                url = request.form.get("url", "").strip()

                if not url:
                    return redirect("/?error=URL is required")

                # Basic URL validation
                if not url.startswith(("http://", "https://")):
                    return redirect(
                        "/?error=Invalid URL (must start with http:// or https://)"
                    )

                # Get texts file path
                texts_file = self._get_texts_file()

                # Append URL to texts file
                with open(texts_file, "a") as f:
                    f.write(f"{url}\n")

                logger.info(f"URL added via web interface: {url}")
                return redirect("/?success=1")

            except ValueError as e:
                logger.error(f"Configuration error: {e}")
                return redirect(f"/?error=Configuration error: {str(e)}")
            except Exception as e:
                logger.error(f"Error adding URL: {e}", exc_info=True)
                return redirect(f"/?error={str(e)}")

        @self.app.route("/add-text", methods=["POST"])
        def add_text():
            """Process free text directly."""
            try:
                text = request.form.get("text", "").strip()
                title = request.form.get("title", "").strip()
                debug_mode = request.form.get("debug") == "1"

                if not text:
                    return redirect("/?error=Text is required")

                if not title:
                    return redirect("/?error=Title is required")

                logger.info(
                    f"Processing free text via web interface: {title} (debug={debug_mode})"
                )

                text_config = self.config.processing.text

                # Debug mode: process synchronously and show result
                if debug_mode:
                    try:
                        original_word_count = len(text.split())
                        processed_text = text

                        if text_config.strategy == "condense":
                            logger.info(f"Debug: Condensing text for: {title}")
                            processed_text = condense_text(
                                text,
                                text_config.model,
                                text_config.condense_ratio,
                                text_config.provider,
                            )

                        processed_word_count = len(processed_text.split())
                        ratio = (
                            processed_word_count / original_word_count
                            if original_word_count > 0
                            else 0
                        )

                        return self._render_debug_result(
                            title=title,
                            original_text=text,
                            processed_text=processed_text,
                            original_word_count=original_word_count,
                            processed_word_count=processed_word_count,
                            ratio=ratio,
                            model=text_config.model,
                            provider=text_config.provider,
                            strategy=text_config.strategy,
                            target_ratio=text_config.condense_ratio,
                        )
                    except Exception as e:
                        logger.error(f"Debug processing error: {e}", exc_info=True)
                        return redirect(f"/?error=Debug processing failed: {str(e)}")

                # Normal mode: process in background thread
                def process_text_background():
                    try:
                        audio_config = self.config.processing.audio
                        processed_text = text

                        # Condense if enabled
                        if text_config.strategy == "condense":
                            logger.info(f"Condensing text for: {title}")
                            processed_text = condense_text(
                                text,
                                text_config.model,
                                text_config.condense_ratio,
                                text_config.provider,
                            )

                        # Process to audio
                        process_text_to_audio(
                            text=processed_text,
                            title=title,
                            vendor=audio_config.vendor,
                            directory=audio_config.output_dir,
                            audio_format=audio_config.format,
                            model=audio_config.model,
                            voice=audio_config.voice,
                            strip=None,
                            destinations=self.config.destinations
                            if self.config.destinations
                            else None,
                        )

                        logger.info(f"Successfully processed free text: {title}")

                    except Exception as e:
                        logger.error(
                            f"Error processing free text '{title}': {e}", exc_info=True
                        )

                threading.Thread(target=process_text_background, daemon=True).start()

                return redirect("/?success_text=1")

            except Exception as e:
                logger.error(f"Error submitting text: {e}", exc_info=True)
                return redirect(f"/?error={str(e)}")

    def start(self):
        """Start the server in a separate thread."""
        if not self.config.server.enabled:
            logger.info("Web server is disabled in configuration")
            return

        # Auto-generate base_url if not set
        if not self.config.server.base_url:
            self.config.server.base_url = (
                f"http://{self.config.server.host}:{self.config.server.port}"
            )

        logger.info(
            f"Starting HTTP server on {self.config.server.host}:{self.config.server.port}"
        )

        # Disable Flask's default logging
        log = logging.getLogger("werkzeug")
        log.setLevel(logging.WARNING)

        def run_server():
            self.app.run(
                host=self.config.server.host,
                port=self.config.server.port,
                debug=False,
                use_reloader=False,
                threaded=True,
            )

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()

        logger.info(f"Web interface available at: {self.config.server.base_url}")

    def stop(self):
        """Stop the server."""
        logger.info("Stopping HTTP server...")
        # Flask doesn't have a clean way to stop from another thread
        # The daemon thread will be terminated when the main program exits
