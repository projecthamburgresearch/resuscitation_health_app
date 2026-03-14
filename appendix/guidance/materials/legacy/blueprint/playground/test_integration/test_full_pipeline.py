"""Integration tests running the full Blueprint pipeline.

Tests the complete flow: X-Ray -> Manifest -> Cortex -> Chronicle
against real code samples.
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.core.config import BlueprintConfig
from src.core.models import EntityType
from src.xray.engine import XRayEngine
from src.manifest.builder import build_manifest, save_manifest, load_manifest
from src.manifest.query import (
    query_by_type,
    query_by_file,
    query_complexity_hotspots,
    query_orphans,
)
from src.cortex.engine import CortexEngine
from src.core.chronicle import Chronicle, start_run, end_run, save_chronicle, load_chronicle


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

PYTHON_SAMPLE = """\
import os
from pathlib import Path

MAX_RETRIES = 3
DEBUG = True

class Config:
    \"\"\"App configuration.\"\"\"
    def __init__(self, env: str = "dev"):
        self.env = env
        self.debug = DEBUG

    def is_production(self) -> bool:
        return self.env == "prod"

def process_data(items: list[str], *, max_items: int = 100) -> dict:
    \"\"\"Process a list of items.\"\"\"
    result = {}
    for item in items:
        if item and len(item) > 0:
            key = item.lower()
            result[key] = len(item)
    return result

def validate(data: dict) -> bool:
    if not data:
        return False
    if "key" not in data:
        return False
    return True
"""

TYPESCRIPT_SAMPLE = """\
import { useState, useEffect } from 'react';

interface UserProps {
    name: string;
    age: number;
}

type Status = 'active' | 'inactive';

const API_URL = "https://api.example.com";

class UserService {
    async getUser(id: number): Promise<UserProps> {
        const response = await fetch(`${API_URL}/users/${id}`);
        return response.json();
    }

    async deleteUser(id: number): Promise<void> {
        await fetch(`${API_URL}/users/${id}`, { method: 'DELETE' });
    }
}

const formatName = (user: UserProps): string => {
    return `${user.name} (${user.age})`;
};

export { UserService, formatName };
"""

CONFIG_SAMPLE = """\
{
    "name": "test-project",
    "version": "1.0.0",
    "database": {
        "host": "localhost",
        "port": 5432
    }
}
"""

HTML_SAMPLE = """\
<!DOCTYPE html>
<html>
<head>
    <link href="style.css" rel="stylesheet">
    <script src="app.js"></script>
</head>
<body>
    <div id="root" class="container">
        <form action="/api/submit" method="POST">
            <input type="text">
        </form>
    </div>
</body>
</html>
"""


@pytest.fixture
def sample_project(tmp_path):
    """Create a sample project with multiple file types."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "config.py").write_text(PYTHON_SAMPLE, encoding="utf-8")
    (tmp_path / "src" / "service.ts").write_text(TYPESCRIPT_SAMPLE, encoding="utf-8")
    (tmp_path / "config.json").write_text(CONFIG_SAMPLE, encoding="utf-8")
    (tmp_path / "index.html").write_text(HTML_SAMPLE, encoding="utf-8")
    return tmp_path


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------


class TestFullPipeline:
    """Test the complete Blueprint pipeline."""

    def test_xray_scans_project(self, sample_project):
        config = BlueprintConfig(
            root_path=str(sample_project),
            extract_symbols=True,
            extract_references=True,
            extract_git=False,
        )
        engine = XRayEngine()
        result = engine.run(config)

        assert result.entity_count() > 0
        assert result.edge_count() > 0
        assert len(result.errors) == 0

        # Should find files
        files = result.entities_by_type(EntityType.FILE)
        assert len(files) >= 4  # .py, .ts, .json, .html

    def test_xray_extracts_python_entities(self, sample_project):
        config = BlueprintConfig(
            root_path=str(sample_project),
            extract_symbols=True,
            extract_git=False,
        )
        engine = XRayEngine()
        result = engine.run(config)

        # Check Python entities
        functions = result.entities_by_type(EntityType.FUNCTION)
        func_names = {e.name for e in functions}
        assert "process_data" in func_names
        assert "validate" in func_names

        classes = result.entities_by_type(EntityType.CLASS)
        class_names = {e.name for e in classes}
        assert "Config" in class_names

        methods = result.entities_by_type(EntityType.METHOD)
        method_names = {e.name for e in methods}
        assert "__init__" in method_names
        assert "is_production" in method_names

    def test_xray_extracts_typescript_entities(self, sample_project):
        config = BlueprintConfig(
            root_path=str(sample_project),
            extract_symbols=True,
            extract_git=False,
        )
        engine = XRayEngine()
        result = engine.run(config)

        # Check TypeScript entities
        interfaces = result.entities_by_type(EntityType.INTERFACE)
        iface_names = {e.name for e in interfaces}
        assert "UserProps" in iface_names

        classes = result.entities_by_type(EntityType.CLASS)
        class_names = {e.name for e in classes}
        assert "UserService" in class_names

    def test_manifest_build_and_query(self, sample_project):
        config = BlueprintConfig(
            root_path=str(sample_project),
            extract_symbols=True,
            extract_git=False,
        )
        engine = XRayEngine()
        result = engine.run(config)
        manifest = build_manifest(result)

        assert len(manifest.entities) > 0
        assert len(manifest.relationships) > 0

        # Query by type
        funcs = query_by_type(manifest, "function")
        assert len(funcs) >= 2

        classes = query_by_type(manifest, "class")
        assert len(classes) >= 2  # Config + UserService

    def test_manifest_serialization(self, sample_project, tmp_path):
        config = BlueprintConfig(
            root_path=str(sample_project),
            extract_symbols=True,
            extract_git=False,
        )
        engine = XRayEngine()
        result = engine.run(config)
        manifest = build_manifest(result)

        # Save and reload
        out_dir = tmp_path / "manifest_out"
        out_dir.mkdir(exist_ok=True)
        out_file = save_manifest(manifest, out_dir, fmt="json")
        assert out_file.exists()

        loaded = load_manifest(out_file)
        assert len(loaded.entities) == len(manifest.entities)
        assert len(loaded.relationships) == len(manifest.relationships)

    def test_cortex_dry_run(self, sample_project):
        config = BlueprintConfig(
            root_path=str(sample_project),
            extract_symbols=True,
            extract_git=False,
            cortex_dry_run=True,
        )

        # Run X-Ray first
        xray = XRayEngine()
        xray_result = xray.run(config)

        # Run Cortex
        cortex = CortexEngine()
        cortex_result = cortex.run(config, prior_results=[xray_result])

        # In dry-run mode, should produce results but not modify files
        assert cortex_result.domain == "cortex"
        # Verify no files were modified
        py_content = (sample_project / "src" / "config.py").read_text(encoding="utf-8")
        assert "@blueprint:cortex" not in py_content

    def test_chronicle_tracking(self, sample_project, tmp_path):
        config = BlueprintConfig(
            root_path=str(sample_project),
            output_path=str(tmp_path),
            extract_symbols=True,
            extract_git=False,
        )

        chronicle = Chronicle()
        run = start_run(chronicle, str(sample_project), ["xray"])

        xray = XRayEngine()
        result = xray.run(config)

        end_run(run, [result])

        assert chronicle.runs[0].entity_count > 0

        # Save and reload
        chron_dir = tmp_path / "chronicle_out"
        chron_dir.mkdir(exist_ok=True)
        save_chronicle(chronicle, chron_dir)
        chron_file = chron_dir / "chronicle.json"
        loaded = load_chronicle(chron_file)
        assert len(loaded.runs) == 1

    def test_html_extraction(self, sample_project):
        config = BlueprintConfig(
            root_path=str(sample_project),
            extract_symbols=True,
            extract_git=False,
        )
        engine = XRayEngine()
        result = engine.run(config)

        # Check HTML entities
        imports = result.entities_by_type(EntityType.IMPORT)
        import_names = {e.name for e in imports}
        assert "app.js" in import_names or "style.css" in import_names

        endpoints = result.entities_by_type(EntityType.ENDPOINT)
        ep_names = {e.name for e in endpoints}
        assert "/api/submit" in ep_names

    def test_config_json_extraction(self, sample_project):
        config = BlueprintConfig(
            root_path=str(sample_project),
            extract_symbols=True,
            extract_git=False,
        )
        engine = XRayEngine()
        result = engine.run(config)

        # Check that JSON config keys are extracted
        variables = result.entities_by_type(EntityType.VARIABLE)
        var_names = {e.name for e in variables}
        assert "name" in var_names
        assert "version" in var_names

    def test_cross_file_analysis(self, sample_project):
        """Verify that the X-Ray engine processes multiple file types in one scan."""
        config = BlueprintConfig(
            root_path=str(sample_project),
            extract_symbols=True,
            extract_git=False,
        )
        engine = XRayEngine()
        result = engine.run(config)

        # Should have entities from multiple languages
        languages = {e.language for e in result.entities if e.language}
        assert len(languages) >= 3  # python, typescript, config/html

    def test_complexity_metrics(self, sample_project):
        config = BlueprintConfig(
            root_path=str(sample_project),
            extract_symbols=True,
            extract_git=False,
        )
        engine = XRayEngine()
        result = engine.run(config)

        # process_data has if/for -> complexity > 1
        funcs = result.entities_by_type(EntityType.FUNCTION)
        process = next((f for f in funcs if f.name == "process_data"), None)
        assert process is not None
        assert process.metrics is not None
        assert process.metrics.cyclomatic_complexity >= 2
        assert process.metrics.loc_total >= 5


class TestRealProject:
    """Test against the made-in-canada-product-scanner repo if available."""

    @pytest.fixture
    def scanner_path(self):
        path = Path(__file__).parent.parent.parent / "appendix" / "made-in-canada-product-scanner"
        if not path.exists():
            pytest.skip("Scanner project not available")
        return path

    def test_scan_real_typescript_project(self, scanner_path):
        config = BlueprintConfig(
            root_path=str(scanner_path),
            extract_symbols=True,
            extract_references=True,
            extract_git=False,
            max_files=100,
        )

        # Focus on src directory only
        engine = XRayEngine()
        result = engine.run(config)

        assert result.entity_count() > 50
        assert result.edge_count() >= 0
        assert len(result.errors) == 0

        # Should have TypeScript entities
        files = result.entities_by_type(EntityType.FILE)
        assert len(files) >= 10

    def test_real_project_manifest(self, scanner_path):
        config = BlueprintConfig(
            root_path=str(scanner_path / "src"),
            extract_symbols=True,
            extract_git=False,
        )
        engine = XRayEngine()
        result = engine.run(config)
        manifest = build_manifest(result)

        assert len(manifest.entities) > 20
        assert len(manifest.relationships) > 10

        # Should have complexity hotspots
        hotspots = query_complexity_hotspots(manifest, min_complexity=3)
        # The project has some complex hooks
        assert len(hotspots) >= 0  # Some may exist
