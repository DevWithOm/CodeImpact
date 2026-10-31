"""Unit tests for static application entry-point detection."""

import json
from pathlib import Path
import pytest

from backend.app.services.dependency_impact.entry_point_detector import (
    detect_entry_points,
)


def test_detect_entry_points_package_json(tmp_path: Path):
    pkg = {
        "name": "my-app",
        "main": "dist/index.js",
        "module": "dist/index.mjs",
        "bin": {"cli": "bin/run.js"},
        "exports": {
            ".": "./dist/index.js",
            "./feature": "./dist/feature.js",
        },
    }
    (tmp_path / "package.json").write_text(json.dumps(pkg), encoding="utf-8")

    entry_points = detect_entry_points(str(tmp_path))
    paths = {ep["file_path"]: ep["entry_point_type"] for ep in entry_points}

    assert "dist/index.js" in paths
    assert paths["dist/index.js"] in ("package_main", "package_export")
    assert "dist/index.mjs" in paths
    assert paths["dist/index.mjs"] == "package_module"
    assert "bin/run.js" in paths
    assert paths["bin/run.js"] == "cli_bin"
    assert "dist/feature.js" in paths
    assert paths["dist/feature.js"] == "package_export"


def test_detect_canonical_source_entry_points(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.ts").write_text("console.log('main');", encoding="utf-8")
    (tmp_path / "src" / "App.tsx").write_text("export default function App() {}", encoding="utf-8")

    entry_points = detect_entry_points(str(tmp_path))
    paths = {ep["file_path"]: ep["entry_point_type"] for ep in entry_points}

    assert "src/main.ts" in paths
    assert paths["src/main.ts"] == "application_entry"
    assert "src/App.tsx" in paths
    assert paths["src/App.tsx"] == "application_entry"


def test_detect_entry_points_from_graph_nodes():
    nodes = ["src/index.ts", "src/utils.ts", "src/services/auth.ts"]
    entry_points = detect_entry_points(repo_path=None, graph_nodes=nodes)

    assert len(entry_points) == 1
    assert entry_points[0]["file_path"] == "src/index.ts"
    assert entry_points[0]["entry_point_type"] == "application_entry"
    assert entry_points[0]["entry_point_status"] == "found"


def test_detect_entry_points_empty():
    assert detect_entry_points(repo_path=None, graph_nodes=[]) == []

