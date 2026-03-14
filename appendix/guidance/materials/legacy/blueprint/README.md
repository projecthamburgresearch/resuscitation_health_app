# Blueprint

**Codebase analysis and understanding tool with autonomous LLM operation.**

Blueprint extracts structure, dependencies, and patterns from codebases. The Warden agent operates Blueprint autonomously with guardrails, memory, and decision logging.

---

## Features

- **Multi-language parsing**: Python, TypeScript, JavaScript, Go, Rust, Java, C#, C++
- **Six analysis domains**: Entity extraction, project structure, dependencies, symbol indexing, quality metrics, cross-references
- **Autonomous operation**: Warden agent with persistent memory and decision audit trail
- **Portable bundles**: Analysis results travel with projects
- **Boot gating**: Certificate system ensures codebase integrity before operation

---

## Quick Start

### CLI Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Analyze a project
python -m src.cli run ./path/to/project

# With specific domains
python -m src.cli run ./project --domains xray,manifest,cortex

# Focus on subdirectory
python -m src.cli run ./project --focus src/api
```

### Warden Commands (in chat)

```
@warden/status              # Check if ready
@warden/analyze ./project   # Set up analysis
@warden/run                 # Execute
@warden/errors              # Check for problems
@warden/recover             # Get fix suggestions
```

See [USER.md](USER.md) for complete command reference.

---

## Analysis Domains

| Domain | Purpose | Output |
|--------|---------|--------|
| **xray** | Extract entities (functions, classes, components) | Entities, edges, call graphs |
| **manifest** | Map project structure | Directory tree, framework detection |
| **cortex** | Analyze dependencies | Import graphs, package dependencies |
| **registry** | Index symbols | Searchable symbol table |
| **sonar** | Calculate metrics | Complexity, coverage, issues |
| **synapse** | Find cross-references | API calls, file references |

---

## Warden Agent

The Warden is an LLM operator that runs Blueprint autonomously:

### Capabilities
- Analyze projects with configurable domains
- Make logged decisions with confidence levels
- Remember learnings across sessions
- Recover gracefully from errors
- Create checkpoints before risky operations

### Limitations
- **No code modification** (analyze only)
- **No external access** (local files only)
- **No secrets handling**
- **No system changes**

### Boot Gating

Warden can only operate when:
1. All mimic tests pass (94 process simulation tests)
2. A valid certificate is issued
3. Certificate hasn't expired (24 hours)
4. `src/` hasn't changed since certificate was issued

```
@warden/certificate         # Check status
@warden/certificate issue   # Run tests and issue
```

---

## Configuration

### deploy.yaml

```yaml
version: "1.0"

targets:
  - type: local
    name: my-app
    path: ./my-app
    focus: src/

domains:
  - xray
  - manifest
  - cortex

purpose: "Analyze component relationships"

warden:
  auto_recover: true
  checkpoint_before_changes: true
  sync_after_run: true
  max_retries: 3
```

### Presets

| Preset | Domains |
|--------|---------|
| `minimal` | xray |
| `standard` | xray, manifest, cortex, registry |
| `full` | All six domains |

---

## Project Structure

```
blueprint/
├── src/
│   ├── core/          # Infrastructure (bundle, sync, certificate)
│   ├── loader/        # Configuration and orchestration
│   ├── warden/        # LLM operator agent
│   ├── xray/          # Entity extraction
│   ├── manifest/      # Project structure
│   ├── cortex/        # Dependencies
│   ├── registry/      # Symbol index
│   ├── sonar/         # Quality metrics
│   └── synapse/       # Cross-references
├── workspace/         # Runtime data
├── playground/        # Tests (721+)
├── USER.md            # User guide
├── SITEMAP.md         # Full structure
└── README.md          # This file
```

See [SITEMAP.md](SITEMAP.md) for complete structure.

---

## Bundle System

Analysis results are stored in portable bundles within projects:

```
my-project/
├── src/
└── my-project_blueprint/    # Portable bundle
    ├── bundle.json          # Manifest
    ├── last-run/            # Latest results
    ├── results/             # Historical runs
    └── warden/              # Warden state
```

Bundles travel with projects and can be imported on any machine.

---

## Testing

```bash
# Run all tests
python -m pytest playground/ -v

# Run mimic tests only (process simulation)
python -m pytest playground/mimic_*/ -v

# Run unit tests only
python -m pytest playground/test_*/ -v
```

**Test counts:**
- Mimic tests: 94 (process simulation)
- Unit tests: 627+ (component testing)
- Total: 721+

---

## Documentation

| Document | Purpose |
|----------|---------|
| [USER.md](USER.md) | User guide and command reference |
| [SITEMAP.md](SITEMAP.md) | Complete project structure |
| [src/warden/AGENT.md](src/warden/AGENT.md) | Warden agent specification |
| [src/warden/COMMANDS.md](src/warden/COMMANDS.md) | All Warden commands |
| [CHANGELOG.md](CHANGELOG.md) | Version history |

---

## Version

**Blueprint v0.2.0**

Key features in this version:
- Warden agent system with memory and decisions
- Certificate-based boot gating
- Bundle portability with warden state sync
- 94 mimic tests for process simulation
- Chat commands (`@warden/...`)

---

## License

Private project.
