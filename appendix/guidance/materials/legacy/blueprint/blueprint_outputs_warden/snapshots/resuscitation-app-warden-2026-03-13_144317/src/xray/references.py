"""Reference detection for X-Ray.

Detects HTTP requests (fetch/axios), API endpoints (express/fastapi/flask),
SQL table references, URL/path references, and file references.
Ported and extended from xray_local.py regex patterns.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from src.core.models import (
    Edge,
    Entity,
    EntityType,
    Evidence,
    Location,
    RelationType,
)


# ---------------------------------------------------------------------------
# Compiled regex patterns
# ---------------------------------------------------------------------------

# HTTP client calls
FETCH_RE = re.compile(
    r"\bfetch\s*\(\s*([`'\"])(.+?)\1",
    re.IGNORECASE,
)
AXIOS_RE = re.compile(
    r"\baxios\.(get|post|put|delete|patch)\s*\(\s*([`'\"])(.+?)\2",
    re.IGNORECASE,
)
HTTPX_RE = re.compile(
    r"\bhttpx?\.(get|post|put|delete|patch)\s*\(\s*([`'\"])(.+?)\2",
    re.IGNORECASE,
)
REQUESTS_RE = re.compile(
    r"\brequests\.(get|post|put|delete|patch)\s*\(\s*([`'\"])(.+?)\2",
    re.IGNORECASE,
)

# Server endpoint declarations
EXPRESS_ROUTE_RE = re.compile(
    r"\b(app|router)\.(get|post|put|delete|patch)\s*\(\s*([`'\"])(.+?)\3",
    re.IGNORECASE,
)
FASTAPI_ROUTE_RE = re.compile(
    r"@app\.(get|post|put|delete|patch)\(\s*([`'\"])(.+?)\2",
    re.IGNORECASE,
)
FLASK_ROUTE_RE = re.compile(
    r"@app\.route\(\s*([`'\"])(.+?)\1\s*(?:,\s*methods\s*=\s*\[([^\]]+)\])?",
    re.IGNORECASE,
)
NEXTJS_API_RE = re.compile(
    r"export\s+(?:default\s+)?(?:async\s+)?function\s+(GET|POST|PUT|DELETE|PATCH)",
    re.IGNORECASE,
)

# SQL
SQL_TABLE_RE = re.compile(
    r"\b(from|join|into|update|table|create\s+table)\s+([a-zA-Z0-9_\.\"]+)",
    re.IGNORECASE,
)

# URL / path references
URL_RE = re.compile(r"\bhttps?://[^\s\"'<>]+", re.IGNORECASE)
API_PATH_RE = re.compile(
    r"(?<![a-zA-Z0-9_])(/api/[a-zA-Z0-9_\-./:{}<>]+)",
    re.IGNORECASE,
)
REL_PATH_RE = re.compile(
    r"""(?<![a-zA-Z0-9_])(\.{0,2}/[a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+)""",
    re.IGNORECASE,
)

# HTML attributes that contain paths
HTML_ATTR_RE = re.compile(
    r"""\b(?:href|src|data-src|data-href|action)\s*=\s*(['"])(.*?)\1""",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Main detection function
# ---------------------------------------------------------------------------

def detect_references(
    source: str,
    file_path: str,
    lines: List[str],
) -> Tuple[List[Entity], List[Edge]]:
    """Detect API calls, endpoints, SQL tables, and path references.

    Args:
        source: Full source text.
        file_path: Relative file path.
        lines: Source split into lines.

    Returns:
        Tuple of (entities, edges) for detected references.
    """
    entities: List[Entity] = []
    edges: List[Edge] = []
    file_id = f"FILE::{file_path}"

    # Detect HTTP client calls (fetch, axios, httpx, requests)
    _detect_network_requests(source, file_path, file_id, lines, entities, edges)

    # Detect server endpoint declarations
    _detect_endpoints(source, file_path, file_id, lines, entities, edges)

    # Detect SQL table references
    _detect_sql_tables(source, file_path, file_id, lines, entities, edges)

    # Detect URL references
    _detect_urls(source, file_path, file_id, lines, entities, edges)

    # Detect file path references
    _detect_file_refs(source, file_path, file_id, lines, entities, edges)

    return entities, edges


# ---------------------------------------------------------------------------
# Network requests
# ---------------------------------------------------------------------------

def _detect_network_requests(
    source: str,
    file_path: str,
    file_id: str,
    lines: List[str],
    entities: List[Entity],
    edges: List[Edge],
) -> None:
    """Detect fetch(), axios.get(), httpx.get(), requests.get() calls."""
    seen: set = set()

    # fetch()
    for m in FETCH_RE.finditer(source):
        url = m.group(2)
        if url in seen:
            continue
        seen.add(url)
        line = _pos_to_line(source, m.start())
        _add_request_entity(
            entities, edges, file_path, file_id, url, "GET", "fetch",
            line, m.group(0), lines,
        )

    # axios.method()
    for m in AXIOS_RE.finditer(source):
        method = m.group(1).upper()
        url = m.group(3)
        key = f"{method}:{url}"
        if key in seen:
            continue
        seen.add(key)
        line = _pos_to_line(source, m.start())
        _add_request_entity(
            entities, edges, file_path, file_id, url, method, "axios",
            line, m.group(0), lines,
        )

    # httpx.method()
    for m in HTTPX_RE.finditer(source):
        method = m.group(1).upper()
        url = m.group(3)
        key = f"{method}:{url}"
        if key in seen:
            continue
        seen.add(key)
        line = _pos_to_line(source, m.start())
        _add_request_entity(
            entities, edges, file_path, file_id, url, method, "httpx",
            line, m.group(0), lines,
        )

    # requests.method()
    for m in REQUESTS_RE.finditer(source):
        method = m.group(1).upper()
        url = m.group(3)
        key = f"{method}:{url}"
        if key in seen:
            continue
        seen.add(key)
        line = _pos_to_line(source, m.start())
        _add_request_entity(
            entities, edges, file_path, file_id, url, method, "requests",
            line, m.group(0), lines,
        )


def _add_request_entity(
    entities: List[Entity],
    edges: List[Edge],
    file_path: str,
    file_id: str,
    url: str,
    method: str,
    library: str,
    line: int,
    snippet: str,
    lines: List[str],
) -> None:
    """Create a NETWORK_REQUEST entity and CONTAINS_REQUEST edge."""
    entity_id = f"REQ::{file_path}::{method}:{url}"
    entities.append(Entity(
        id=entity_id,
        type=EntityType.NETWORK_REQUEST,
        name=f"{method} {url}",
        qualified_name=url,
        location=Location(file=file_path, start_line=line, end_line=line),
        meta={"method": method, "url": url, "library": library},
    ))
    edges.append(Edge(
        source=file_id,
        target=entity_id,
        relation=RelationType.CONTAINS_REQUEST,
        evidence=[Evidence(
            file=file_path,
            start_line=line,
            end_line=line,
            snippet=snippet[:200],
        )],
    ))


# ---------------------------------------------------------------------------
# Endpoint declarations
# ---------------------------------------------------------------------------

def _detect_endpoints(
    source: str,
    file_path: str,
    file_id: str,
    lines: List[str],
    entities: List[Entity],
    edges: List[Edge],
) -> None:
    """Detect Express, FastAPI, Flask, and Next.js API route declarations."""
    seen: set = set()

    # Express: app.get('/path', ...)
    for m in EXPRESS_ROUTE_RE.finditer(source):
        method = m.group(2).upper()
        path = m.group(4)
        key = f"{method}:{path}"
        if key in seen:
            continue
        seen.add(key)
        line = _pos_to_line(source, m.start())
        _add_endpoint_entity(
            entities, edges, file_path, file_id, path, method, "express",
            line, m.group(0), lines,
        )

    # FastAPI: @app.get('/path')
    for m in FASTAPI_ROUTE_RE.finditer(source):
        method = m.group(1).upper()
        path = m.group(3)
        key = f"{method}:{path}"
        if key in seen:
            continue
        seen.add(key)
        line = _pos_to_line(source, m.start())
        _add_endpoint_entity(
            entities, edges, file_path, file_id, path, method, "fastapi",
            line, m.group(0), lines,
        )

    # Flask: @app.route('/path', methods=['GET'])
    for m in FLASK_ROUTE_RE.finditer(source):
        path = m.group(2)
        methods_str = m.group(3)
        methods = ["GET"]
        if methods_str:
            methods = [s.strip().strip("'\"").upper() for s in methods_str.split(",")]
        for method in methods:
            key = f"{method}:{path}"
            if key in seen:
                continue
            seen.add(key)
            line = _pos_to_line(source, m.start())
            _add_endpoint_entity(
                entities, edges, file_path, file_id, path, method, "flask",
                line, m.group(0), lines,
            )

    # Next.js API routes
    for m in NEXTJS_API_RE.finditer(source):
        method = m.group(1).upper()
        # Path is derived from file location
        path = f"/api/{file_path}"
        key = f"{method}:{path}"
        if key in seen:
            continue
        seen.add(key)
        line = _pos_to_line(source, m.start())
        _add_endpoint_entity(
            entities, edges, file_path, file_id, path, method, "nextjs",
            line, m.group(0), lines,
        )


def _add_endpoint_entity(
    entities: List[Entity],
    edges: List[Edge],
    file_path: str,
    file_id: str,
    path: str,
    method: str,
    framework: str,
    line: int,
    snippet: str,
    lines: List[str],
) -> None:
    """Create an ENDPOINT entity and DECLARES_ENDPOINT edge."""
    entity_id = f"EP::{file_path}::{method}:{path}"
    entities.append(Entity(
        id=entity_id,
        type=EntityType.ENDPOINT,
        name=f"{method} {path}",
        qualified_name=path,
        location=Location(file=file_path, start_line=line, end_line=line),
        meta={"method": method, "path": path, "framework": framework},
    ))
    edges.append(Edge(
        source=file_id,
        target=entity_id,
        relation=RelationType.DECLARES_ENDPOINT,
        evidence=[Evidence(
            file=file_path,
            start_line=line,
            end_line=line,
            snippet=snippet[:200],
        )],
    ))


# ---------------------------------------------------------------------------
# SQL tables
# ---------------------------------------------------------------------------

def _detect_sql_tables(
    source: str,
    file_path: str,
    file_id: str,
    lines: List[str],
    entities: List[Entity],
    edges: List[Edge],
) -> None:
    """Detect SQL table references (FROM, JOIN, INTO, UPDATE, CREATE TABLE)."""
    seen: set = set()

    for m in SQL_TABLE_RE.finditer(source):
        table_name = m.group(2).strip('"').strip("'").strip("`")
        if table_name.lower() in ("select", "set", "values", "where", "null"):
            continue
        if table_name in seen:
            continue
        seen.add(table_name)
        line = _pos_to_line(source, m.start())
        entity_id = f"TABLE::{file_path}::{table_name}"
        entities.append(Entity(
            id=entity_id,
            type=EntityType.TABLE,
            name=table_name,
            qualified_name=table_name,
            location=Location(file=file_path, start_line=line, end_line=line),
            meta={"operation": m.group(1).strip().upper()},
        ))
        edges.append(Edge(
            source=file_id,
            target=entity_id,
            relation=RelationType.TOUCHES_TABLE,
            evidence=[Evidence(
                file=file_path,
                start_line=line,
                end_line=line,
                snippet=m.group(0)[:200],
            )],
        ))


# ---------------------------------------------------------------------------
# URL references
# ---------------------------------------------------------------------------

def _detect_urls(
    source: str,
    file_path: str,
    file_id: str,
    lines: List[str],
    entities: List[Entity],
    edges: List[Edge],
) -> None:
    """Detect HTTP/HTTPS URLs and API path patterns."""
    seen: set = set()

    for m in URL_RE.finditer(source):
        url = m.group(0).rstrip(".,;:)\"'")
        if url in seen:
            continue
        seen.add(url)

    for m in API_PATH_RE.finditer(source):
        path = m.group(1)
        if path in seen:
            continue
        seen.add(path)
        line = _pos_to_line(source, m.start())
        entity_id = f"REF::{file_path}::api_path:{path}"
        entities.append(Entity(
            id=entity_id,
            type=EntityType.CHUNK,
            name=f"API: {path}",
            qualified_name=path,
            location=Location(file=file_path, start_line=line, end_line=line),
            meta={"ref_type": "api_path", "value": path},
        ))
        edges.append(Edge(
            source=file_id,
            target=entity_id,
            relation=RelationType.MENTIONS,
        ))


# ---------------------------------------------------------------------------
# File references
# ---------------------------------------------------------------------------

def _detect_file_refs(
    source: str,
    file_path: str,
    file_id: str,
    lines: List[str],
    entities: List[Entity],
    edges: List[Edge],
) -> None:
    """Detect relative file path references and HTML src/href attributes."""
    seen: set = set()

    # Relative paths
    for m in REL_PATH_RE.finditer(source):
        ref_path = m.group(1)
        # Skip common false positives
        if ref_path.startswith("//"):
            continue
        if ref_path in seen:
            continue
        seen.add(ref_path)
        line = _pos_to_line(source, m.start())
        entity_id = f"REF::{file_path}::file:{ref_path}"
        entities.append(Entity(
            id=entity_id,
            type=EntityType.CHUNK,
            name=ref_path,
            qualified_name=ref_path,
            location=Location(file=file_path, start_line=line, end_line=line),
            meta={"ref_type": "file_path", "value": ref_path},
        ))
        edges.append(Edge(
            source=file_id,
            target=entity_id,
            relation=RelationType.LINKS_TO_FILE,
        ))

    # HTML attributes
    for m in HTML_ATTR_RE.finditer(source):
        href = m.group(2)
        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue
        if href in seen:
            continue
        seen.add(href)
        line = _pos_to_line(source, m.start())
        entity_id = f"REF::{file_path}::href:{href}"
        entities.append(Entity(
            id=entity_id,
            type=EntityType.CHUNK,
            name=href,
            qualified_name=href,
            location=Location(file=file_path, start_line=line, end_line=line),
            meta={"ref_type": "html_attr", "value": href},
        ))
        edges.append(Edge(
            source=file_id,
            target=entity_id,
            relation=RelationType.LINKS_TO_FILE,
        ))


# ---------------------------------------------------------------------------
# Cross-file reference matching
# ---------------------------------------------------------------------------

def resolve_request_endpoint_edges(
    entities: List[Entity],
    edges: List[Edge],
) -> List[Edge]:
    """Match NETWORK_REQUEST entities to ENDPOINT entities by URL path.

    Returns new MATCHES_ENDPOINT edges.
    """
    new_edges: List[Edge] = []

    requests = [e for e in entities if e.type == EntityType.NETWORK_REQUEST]
    endpoints = [e for e in entities if e.type == EntityType.ENDPOINT]

    if not requests or not endpoints:
        return new_edges

    # Build endpoint lookup: path -> entity_id
    ep_by_path: Dict[str, List[str]] = {}
    for ep in endpoints:
        path = ep.meta.get("path", "")
        # Normalize: remove trailing slashes, template params
        normalized = _normalize_api_path(path)
        ep_by_path.setdefault(normalized, []).append(ep.id)

    for req in requests:
        url = req.meta.get("url", "")
        # Extract path from URL
        path = _extract_path_from_url(url)
        normalized = _normalize_api_path(path)

        matched_eps = ep_by_path.get(normalized, [])
        for ep_id in matched_eps:
            new_edges.append(Edge(
                source=req.id,
                target=ep_id,
                relation=RelationType.MATCHES_ENDPOINT,
                confidence=0.9,
                meta={"matched_path": normalized},
            ))

    return new_edges


def _normalize_api_path(path: str) -> str:
    """Normalize an API path for matching."""
    # Remove trailing slash
    path = path.rstrip("/")
    # Replace template params: /users/:id, /users/{id}, /users/<id>
    path = re.sub(r":[a-zA-Z_]+", ":param", path)
    path = re.sub(r"\{[a-zA-Z_]+\}", ":param", path)
    path = re.sub(r"<[a-zA-Z_:]+>", ":param", path)
    return path.lower()


def _extract_path_from_url(url: str) -> str:
    """Extract the path component from a URL or path string."""
    # Remove protocol and host
    if "://" in url:
        url = url.split("://", 1)[1]
        # Remove host
        if "/" in url:
            url = "/" + url.split("/", 1)[1]
        else:
            url = "/"
    # Remove query string
    if "?" in url:
        url = url.split("?", 1)[0]
    return url


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pos_to_line(source: str, pos: int) -> int:
    """Convert a character position to 1-based line number."""
    return source[:pos].count("\n") + 1
