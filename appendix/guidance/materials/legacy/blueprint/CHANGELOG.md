# Changelog

## v0.2.0 - Analysis, Quality & Workspace

Three new analysis domains plus a workspace system for project loading.

### Workspace System
- **Workspace folders**: `intake/` (loading zone), `results/` (output), `control/` (config/profiles)
- **`.bpignore`**: Per-project ignore file (gitignore syntax) - exclude files/folders from analysis. Supports negation (`!pattern`), auto-merges with Blueprint defaults
- **`deploy.yaml`**: Declarative deployment descriptor - local paths, subfolder focus, file lists, GitHub repos (public + private with token auth)
- **Runner**: Orchestrates all domains per-target, timestamped output, `run_meta.json` per run
- **CLI**: `blueprint workspace init`, `workspace run`, `workspace status`
- **Profiles**: `control/profiles/quick.yaml`, `deep.yaml` - reusable presets
- **Auto-discover**: Drop a folder in `intake/local/` and run - no config needed

### New Domains
- **Registry** - Project indexing and zone partitioning. Scans project structure, partitions into zones for parallel processing, builds a master index with caller/callee metadata. Incremental updates and JSON persistence.
- **Sonar** - Code quality scanning. Naming convention checks (Python snake_case/PascalCase, Java/C# camelCase, Go exported names), complexity thresholds (cyclomatic complexity, LOC, nesting depth, parameter count, fan-out), dead code detection (uncalled functions, unreferenced imports, empty classes).
- **Synapse** - Call chain analysis and hotspot detection. Upstream/downstream chain tracing with BFS, execution sequence tracing from entry points with DFS, structural hotspot classification (bottleneck, high fan-in/out, hub, leaf, orphan).

### CLI
- 3 new domain commands: `registry`, `sonar`, `synapse`
- 3 new workspace commands: `workspace init`, `workspace run`, `workspace status`
- `scan` pipeline expanded: X-Ray -> Manifest -> Cortex -> Registry -> Sonar -> Synapse
- 11 commands total

### Tests
- 69 workspace tests + 102 domain tests = 171 new tests
- Total: 546 tests

## v0.1.0 - Foundation

First release. Core static analysis platform with 5 domains.

### Domains
- **X-Ray** - Static code analysis with tree-sitter. 15 language parsers (Python, TypeScript/JS/JSX/TSX, Go, Rust, Java, C#, Ruby, PHP, Swift, Kotlin, C, C++, Config, Web). 44 file extensions. Entity/edge extraction, cyclomatic complexity, fan-in/fan-out, LOC metrics.
- **Manifest** - Knowledge graph index. Build, query, diff, serialize (YAML/JSON).
- **Cortex** - LLM-oriented comment metadata injection. 4 formatters (hash, slash, block, HTML). Dry-run and write modes.
- **Chronicle** - Run history, milestones, delta tracking. JSON persistence.
- **CLI** - 5 commands: `xray`, `manifest`, `cortex`, `scan`, `history`. Cross-platform (no Unicode dependency).

### Infrastructure
- Pydantic v2 models (Entity, Edge, Metrics, Evidence, Location)
- NetworkX knowledge graph with cycle detection, fan analysis, orphan detection
- `pathlib.Path` throughout (Windows/macOS/Linux safe)
- 375 tests, all passing

### Outputs
- `xray_result.json` - Full entity/edge graph
- `llm_context.json` - Condensed LLM bundle (configurable limits)
- `xray_report.md` - Human-readable complexity report
- `manifest.yaml` / `manifest.json` - Knowledge graph index
- `entities.csv` / `edges.csv` - Tabular export
- `sitemap.md` - File tree
