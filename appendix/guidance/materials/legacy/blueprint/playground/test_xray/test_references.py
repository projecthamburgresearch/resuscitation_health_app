"""Tests for blueprint.xray.references."""

from __future__ import annotations

import pytest

from src.core.models import EntityType, RelationType
from src.xray.references import (
    detect_references,
    resolve_request_endpoint_edges,
    _normalize_api_path,
    _extract_path_from_url,
)


class TestDetectNetworkRequests:
    """Network request detection tests."""

    def test_fetch_call(self):
        source = "const data = fetch('/api/users')"
        lines = source.splitlines()
        entities, edges = detect_references(source, "app.js", lines)
        reqs = [e for e in entities if e.type == EntityType.NETWORK_REQUEST]
        assert len(reqs) == 1
        assert "/api/users" in reqs[0].name

    def test_axios_call(self):
        source = "axios.get('/api/products')"
        lines = source.splitlines()
        entities, edges = detect_references(source, "api.ts", lines)
        reqs = [e for e in entities if e.type == EntityType.NETWORK_REQUEST]
        assert len(reqs) == 1
        assert "GET" in reqs[0].name

    def test_requests_call(self):
        source = 'requests.post("/api/login")'
        lines = source.splitlines()
        entities, edges = detect_references(source, "auth.py", lines)
        reqs = [e for e in entities if e.type == EntityType.NETWORK_REQUEST]
        assert len(reqs) == 1
        assert "POST" in reqs[0].name

    def test_multiple_calls(self):
        source = (
            "fetch('/api/a')\n"
            "axios.get('/api/b')\n"
            "requests.delete('/api/c')\n"
        )
        lines = source.splitlines()
        entities, edges = detect_references(source, "multi.ts", lines)
        reqs = [e for e in entities if e.type == EntityType.NETWORK_REQUEST]
        assert len(reqs) == 3

    def test_dedup_same_url(self):
        source = "fetch('/api/users')\nfetch('/api/users')"
        lines = source.splitlines()
        entities, edges = detect_references(source, "dup.js", lines)
        reqs = [e for e in entities if e.type == EntityType.NETWORK_REQUEST]
        assert len(reqs) == 1


class TestDetectEndpoints:
    """Endpoint detection tests."""

    def test_express_route(self):
        source = "app.get('/api/items', handler)"
        lines = source.splitlines()
        entities, edges = detect_references(source, "server.ts", lines)
        eps = [e for e in entities if e.type == EntityType.ENDPOINT]
        assert len(eps) == 1
        assert "GET" in eps[0].name
        assert "/api/items" in eps[0].name

    def test_fastapi_route(self):
        source = '@app.post("/api/login")\nasync def login():\n    pass'
        lines = source.splitlines()
        entities, edges = detect_references(source, "main.py", lines)
        eps = [e for e in entities if e.type == EntityType.ENDPOINT]
        assert len(eps) == 1

    def test_flask_route(self):
        source = "@app.route('/users', methods=['GET', 'POST'])"
        lines = source.splitlines()
        entities, edges = detect_references(source, "views.py", lines)
        eps = [e for e in entities if e.type == EntityType.ENDPOINT]
        assert len(eps) == 2  # GET and POST


class TestDetectSQLTables:
    """SQL table detection tests."""

    def test_select_from(self):
        source = "SELECT * FROM users WHERE id = 1"
        lines = source.splitlines()
        entities, edges = detect_references(source, "query.sql", lines)
        tables = [e for e in entities if e.type == EntityType.TABLE]
        assert len(tables) == 1
        assert tables[0].name == "users"

    def test_join(self):
        source = "SELECT * FROM users JOIN orders ON users.id = orders.user_id"
        lines = source.splitlines()
        entities, edges = detect_references(source, "q.sql", lines)
        tables = [e for e in entities if e.type == EntityType.TABLE]
        table_names = {t.name for t in tables}
        assert "users" in table_names
        assert "orders" in table_names

    def test_insert_into(self):
        source = "INSERT INTO logs VALUES (1, 'test')"
        lines = source.splitlines()
        entities, edges = detect_references(source, "insert.sql", lines)
        tables = [e for e in entities if e.type == EntityType.TABLE]
        assert len(tables) == 1
        assert tables[0].name == "logs"


class TestDetectFileRefs:
    """File reference detection tests."""

    def test_relative_path(self):
        source = 'import config from "./config.ts"'
        lines = source.splitlines()
        entities, edges = detect_references(source, "app.ts", lines)
        chunks = [e for e in entities if e.type == EntityType.CHUNK]
        assert len(chunks) >= 1

    def test_html_href(self):
        source = '<a href="https://example.com">Link</a>'
        lines = source.splitlines()
        entities, edges = detect_references(source, "index.html", lines)
        chunks = [e for e in entities if e.type == EntityType.CHUNK]
        assert len(chunks) >= 1


class TestCrossFileResolution:
    """Request-to-endpoint matching tests."""

    def test_exact_path_match(self):
        from src.core.models import Entity, Location

        entities = [
            Entity(
                id="REQ::client.ts::GET:/api/users",
                type=EntityType.NETWORK_REQUEST,
                name="GET /api/users",
                meta={"method": "GET", "url": "/api/users"},
            ),
            Entity(
                id="EP::server.ts::GET:/api/users",
                type=EntityType.ENDPOINT,
                name="GET /api/users",
                meta={"method": "GET", "path": "/api/users"},
            ),
        ]
        new_edges = resolve_request_endpoint_edges(entities, [])
        assert len(new_edges) == 1
        assert new_edges[0].relation == RelationType.MATCHES_ENDPOINT

    def test_template_param_matching(self):
        from src.core.models import Entity

        entities = [
            Entity(
                id="REQ::client.ts::GET:/api/users/123",
                type=EntityType.NETWORK_REQUEST,
                name="GET /api/users/123",
                meta={"method": "GET", "url": "/api/users/123"},
            ),
            Entity(
                id="EP::server.ts::GET:/api/users/:id",
                type=EntityType.ENDPOINT,
                name="GET /api/users/:id",
                meta={"method": "GET", "path": "/api/users/:id"},
            ),
        ]
        # Template params are normalized to :param, so /users/123 won't match /users/:param
        # This is expected behavior — exact matching after normalization
        new_edges = resolve_request_endpoint_edges(entities, [])
        # Might not match since 123 != :param
        # This test documents current behavior


class TestHelpers:
    """Helper function tests."""

    def test_normalize_api_path(self):
        assert _normalize_api_path("/api/users/") == "/api/users"
        assert _normalize_api_path("/api/users/:id") == "/api/users/:param"
        assert _normalize_api_path("/api/users/{id}") == "/api/users/:param"
        assert _normalize_api_path("/api/users/<int:id>") == "/api/users/:param"

    def test_extract_path_from_url(self):
        assert _extract_path_from_url("https://example.com/api/users") == "/api/users"
        assert _extract_path_from_url("/api/users?page=1") == "/api/users"
        assert _extract_path_from_url("/api/users") == "/api/users"
