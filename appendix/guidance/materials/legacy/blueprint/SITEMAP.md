# Blueprint Project Sitemap

Complete directory structure and file purposes.

---

## Root

```
blueprint/
├── README.md              # Project overview and quick start
├── USER.md                # User guide for interacting with Warden
├── SITEMAP.md             # This file - project structure
├── CHANGELOG.md           # Version history
├── pyproject.toml         # Python project config
├── requirements.txt       # Dependencies
└── .bpignore              # Files to ignore during analysis
```

---

## Source Code (`src/`)

### Core (`src/core/`)
Infrastructure and shared utilities.

```
src/core/
├── __init__.py
├── config.py              # Global configuration
├── domain.py              # Base domain class
├── errors.py              # Custom exceptions
├── graph.py               # Graph data structures
├── io_utils.py            # File I/O utilities
├── models.py              # Shared data models
├── bundle.py              # Project bundle management
├── project.py             # Project lifecycle management
├── snapshot.py            # Snapshot creation/management
├── intra.py               # Intra-run versioning (checkpoints)
├── sync.py                # Workspace-bundle synchronization
└── certificate.py         # Boot certificate system
```

### Loader (`src/loader/`)
Configuration and orchestration.

```
src/loader/
├── __init__.py
├── schema.py              # Pydantic models (DeployConfig, RunMeta)
├── deploy.py              # deploy.yaml parsing
├── runner.py              # Domain orchestration
└── bpignore.py            # .bpignore file handling
```

### Warden (`src/warden/`)
LLM operator agent system.

```
src/warden/
├── __init__.py            # Public exports
├── AGENT.md               # Agent specification (what Warden can/cannot do)
├── COMMANDS.md            # Command reference
├── engine.py              # Core Warden logic
├── config.py              # Warden configuration
├── memory.py              # Persistent memory
├── decisions.py           # Decision audit trail
├── commits.py             # Local version control
└── commands.py            # Chat command handler (@warden/...)
```

### Analysis Domains (`src/`)

```
src/xray/                  # Entity extraction
├── __init__.py
├── domain.py              # Domain implementation
├── models.py              # Entity/Edge models
├── parsers/               # Language-specific parsers
│   ├── base.py
│   ├── python_parser.py
│   ├── typescript_parser.py
│   ├── javascript_parser.py
│   ├── go_parser.py
│   ├── rust_parser.py
│   ├── java_parser.py
│   ├── csharp_parser.py
│   └── cpp_parser.py
├── stats.py               # Parser statistics
└── references.py          # Cross-file references

src/manifest/              # Project structure analysis
├── __init__.py
├── domain.py
├── models.py
├── tree.py                # Directory tree building
└── detector.py            # Framework detection

src/cortex/                # Dependency analysis
├── __init__.py
├── domain.py
├── models.py
├── resolver.py            # Import resolution
└── parsers/               # Package file parsers

src/registry/              # Symbol indexing
├── __init__.py
├── domain.py
├── models.py
└── indexer.py

src/sonar/                 # Quality metrics
├── __init__.py
├── domain.py
├── models.py
├── metrics.py             # Metric calculations
└── detectors/             # Issue detectors

src/synapse/               # Cross-reference analysis
├── __init__.py
├── domain.py
├── models.py
└── linker.py              # Reference linking
```

### CLI (`src/cli.py`)
Command-line interface.

---

## Workspace (`workspace/`)

Runtime data and state.

```
workspace/
├── intake/                # Input
│   ├── deploy.yaml        # Run configuration
│   └── local/             # Local project links
│
├── results/               # Output
│   └── {project}/
│       └── {run-id}/
│           ├── xray.json
│           ├── manifest.json
│           ├── cortex.json
│           └── ...
│
├── snapshots/             # Project snapshots
│   └── {project}/
│       └── snap-{id}/
│           └── src/       # Copied source
│
├── warden/                # Warden state
│   ├── config.yaml
│   ├── memory/
│   │   └── memory.json
│   ├── decisions/
│   │   └── decisions.json
│   ├── commits/
│   │   └── commits.json
│   └── errors.json
│
├── status/                # Run status
│   └── health.json
│
├── control/               # Control files
│   └── certificates/
│       └── current.json
│
└── projects/              # Project registry
    └── {project}/
        └── project.json
```

---

## Playground (`playground/`)

Tests organized by type.

```
playground/
├── mimic_*/               # Process simulation tests (mimic tests)
│   ├── mimic_boot/        # Boot process tests
│   ├── mimic_run/         # Run process tests
│   ├── mimic_intra/       # Checkpoint/revert tests
│   ├── mimic_project/     # Project management tests
│   ├── mimic_bundle/      # Bundle import/export tests
│   ├── mimic_sync/        # Sync process tests
│   ├── mimic_certificate/ # Certificate lifecycle tests
│   └── mimic_warden/      # Warden operation tests
│
├── test_*/                # Unit tests by domain
│   ├── test_xray/
│   ├── test_manifest/
│   ├── test_cortex/
│   ├── test_registry/
│   ├── test_sonar/
│   ├── test_synapse/
│   ├── test_loader/
│   ├── test_core/
│   ├── test_integration/
│   └── test_chronicle/
│
└── conftest.py            # Shared fixtures
```

---

## Bundle Structure (in analyzed projects)

When Blueprint analyzes a project, it can create a portable bundle:

```
my-project/
├── src/                   # Project source
├── package.json           # Project config
└── my-project_blueprint/  # Blueprint bundle
    ├── bundle.json        # Manifest
    ├── last-run/          # Most recent results
    ├── results/           # Historical results
    │   └── {run-id}/
    ├── configs/           # deploy.yaml snapshots
    └── warden/            # Warden state
        ├── commits/
        ├── decisions/
        └── memory_summary.json
```

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `src/warden/AGENT.md` | What Warden can/cannot do |
| `src/warden/COMMANDS.md` | All @warden/ commands |
| `USER.md` | How to use Blueprint |
| `workspace/intake/deploy.yaml` | Run configuration |
| `workspace/warden/memory/memory.json` | Warden's persistent memory |
| `workspace/warden/decisions/decisions.json` | Decision audit trail |
| `workspace/control/certificates/current.json` | Boot certificate |

---

## Data Flow

```
1. User provides project path
         ↓
2. deploy.yaml configures analysis
         ↓
3. Certificate validates src/ (mimic tests pass)
         ↓
4. Snapshot copies source to workspace/snapshots/
         ↓
5. Domains analyze snapshot (xray → manifest → cortex → ...)
         ↓
6. Results saved to workspace/results/{project}/{run-id}/
         ↓
7. Warden logs decisions, updates memory
         ↓
8. Bundle syncs results to project_blueprint/ (portable)
```

---

## Test Categories

| Pattern | Type | Count | Purpose |
|---------|------|-------|---------|
| `mimic_*` | Process | 94 | Full workflow simulation |
| `test_*` | Unit | 627+ | Component testing |
| **Total** | | 721+ | |

Certificate system requires all mimic tests to pass before Warden can boot.
