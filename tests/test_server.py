"""Tests for the Textcast server API endpoints."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from textcast.server import TextcastServer
from textcast.service_config import ServiceConfig, load_config


@pytest.fixture
def server_app(tmp_path):
    """Create a test Flask app with a minimal config."""
    texts_file = tmp_path / "Texts.txt"
    texts_file.touch()

    config_path = tmp_path / "config.yaml"
    config_path.write_text(f"""
check_interval: 5m
sources:
  - type: file
    name: test
    enabled: true
    file: {texts_file}
processing:
  text:
    provider: anthropic
    strategy: condense
  audio:
    vendor: openai
    output_dir: {tmp_path}/audio
server:
  enabled: true
  host: 127.0.0.1
  port: 8084
""")

    config = load_config(str(config_path))
    server = TextcastServer(config)
    server.app.testing = True
    return server.app, texts_file


class TestApiUrls:
    """Tests for POST /api/urls."""

    def test_add_single_url(self, server_app):
        app, texts_file = server_app
        with app.test_client() as client:
            resp = client.post("/api/urls", json={"url": "https://example.com/article"})
            assert resp.status_code == 202
            data = resp.get_json()
            assert data["success"] is True
            assert data["count"] == 1
            assert "https://example.com/article" in texts_file.read_text()

    def test_add_multiple_urls(self, server_app):
        app, texts_file = server_app
        with app.test_client() as client:
            resp = client.post("/api/urls", json={
                "urls": ["https://example.com/a", "https://example.com/b"]
            })
            assert resp.status_code == 202
            data = resp.get_json()
            assert data["count"] == 2
            content = texts_file.read_text()
            assert "https://example.com/a" in content
            assert "https://example.com/b" in content

    def test_missing_body(self, server_app):
        app, _ = server_app
        with app.test_client() as client:
            resp = client.post("/api/urls", content_type="application/json")
            assert resp.status_code == 400

    def test_malformed_json(self, server_app):
        app, _ = server_app
        with app.test_client() as client:
            resp = client.post(
                "/api/urls",
                data="not json",
                content_type="application/json",
            )
            assert resp.status_code == 400

    def test_wrong_content_type(self, server_app):
        app, _ = server_app
        with app.test_client() as client:
            resp = client.post(
                "/api/urls",
                data="url=https://example.com",
                content_type="application/x-www-form-urlencoded",
            )
            assert resp.status_code == 400

    def test_url_not_string(self, server_app):
        app, _ = server_app
        with app.test_client() as client:
            resp = client.post("/api/urls", json={"url": 123})
            assert resp.status_code == 400

    def test_invalid_url_scheme(self, server_app):
        app, _ = server_app
        with app.test_client() as client:
            resp = client.post("/api/urls", json={"url": "ftp://example.com"})
            assert resp.status_code == 400

    def test_empty_url(self, server_app):
        app, _ = server_app
        with app.test_client() as client:
            resp = client.post("/api/urls", json={"url": ""})
            assert resp.status_code == 400

    def test_no_url_or_urls_field(self, server_app):
        app, _ = server_app
        with app.test_client() as client:
            resp = client.post("/api/urls", json={"foo": "bar"})
            assert resp.status_code == 400


class TestApiText:
    """Tests for POST /api/text."""

    def test_submit_text(self, server_app):
        app, _ = server_app
        with app.test_client() as client:
            with patch.object(TextcastServer, "_process_text_in_background"):
                resp = client.post("/api/text", json={
                    "title": "Test Article",
                    "text": "Some article content here.",
                })
                assert resp.status_code == 202
                data = resp.get_json()
                assert data["success"] is True
                assert data["title"] == "Test Article"

    def test_missing_text(self, server_app):
        app, _ = server_app
        with app.test_client() as client:
            resp = client.post("/api/text", json={"title": "Test"})
            assert resp.status_code == 400
            assert "text" in resp.get_json()["error"]

    def test_missing_title(self, server_app):
        app, _ = server_app
        with app.test_client() as client:
            resp = client.post("/api/text", json={"text": "Some text"})
            assert resp.status_code == 400
            assert "title" in resp.get_json()["error"]

    def test_title_not_string(self, server_app):
        app, _ = server_app
        with app.test_client() as client:
            resp = client.post("/api/text", json={"title": 123, "text": "content"})
            assert resp.status_code == 400

    def test_text_not_string(self, server_app):
        app, _ = server_app
        with app.test_client() as client:
            resp = client.post("/api/text", json={"title": "Test", "text": ["not", "a", "string"]})
            assert resp.status_code == 400

    def test_malformed_json(self, server_app):
        app, _ = server_app
        with app.test_client() as client:
            resp = client.post(
                "/api/text",
                data="{bad",
                content_type="application/json",
            )
            assert resp.status_code == 400

    def test_empty_body(self, server_app):
        app, _ = server_app
        with app.test_client() as client:
            resp = client.post("/api/text", content_type="application/json")
            assert resp.status_code == 400
